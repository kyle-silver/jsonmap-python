"""
Transform raw source input into a token stream which can then be assembled into
an abstract syntax tree
"""

from __future__ import annotations

from abc import ABC
from dataclasses import dataclass
from enum import IntEnum, auto
from typing import List, Optional, Tuple

from more_itertools import peekable

from jsonmap.error import JsonMapSyntaxError


# just for the ease of reading type signatures
Char = Tuple[int, str]


# pylint: disable=invalid-name
class Symbol(IntEnum):
    """
    The different categories of tokens, which we will later assemble into the
    AST
    """

    end_of_statement = auto()
    assignment = auto()
    left_curly_brace = auto()
    right_curly_brace = auto()
    left_square_bracket = auto()
    right_square_bracket = auto()


@dataclass(frozen=True)
class Token(ABC):
    """Represents a single AST token"""

    position: int

    def is_symbol(self, symbol: Symbol) -> bool:
        """Test if this token instance is a symbol literal"""
        return isinstance(self, SymbolToken) and self.symbol == symbol  # pylint: disable=no-member


@dataclass(frozen=True)
class SymbolToken(Token):
    """Represents a language symbol"""

    symbol: Symbol


@dataclass(frozen=True)
class BareWord(Token):
    """Represents a language keyword"""

    value: str


@dataclass(frozen=True)
class LiteralToken(Token):
    """Token which contains a literal value"""

    text: str


@dataclass(frozen=True)
class InterpolationToken(Token):
    """Token which contains a literal value"""

    pattern: str


@dataclass(frozen=True)
class ReferenceToken(Token):
    """Token which references a namespace in the input JSON"""

    path: List[str]
    global_scope: bool = False


def capture_string(stream: peekable[Char], delimiter: str) -> str:
    """
    Walk through the iterable and pull out a string literal sequence from the
    source code.
    """
    token = []
    while (item := next(stream))[1] != delimiter:
        _, char = item
        token.append(char)
    return "".join(token)


def capture_bare_word(stream: peekable[Char], *, delimiters: List[str], first: Optional[str] = None) -> str:
    """Capture text which is not in quotation marks"""
    token = [first] if first else []
    while item := stream.peek():
        _, next_char = item
        if next_char in delimiters:
            break
        if next_char.isspace():
            next(stream)
            break
        token.append(next_char)
        next(stream)  # pop
    return "".join(token)


def parse_reference(stream: peekable[Char]) -> ReferenceToken:
    """
    A field reference is a RHS expression referencing data from the input JSON
    """
    path: List[str] = []
    global_scope = False
    position = None
    while item := stream.peek():
        current_position, next_char = item
        if position is None:
            position = current_position  # only assign this once, the first time
        match next_char:
            case ".":
                next(stream)  # pop the item
            case "!":
                if len(path) > 0:
                    raise JsonMapSyntaxError(current_position, 'Illegal element in path "!"')
                global_scope = True
                next(stream)
            case '"':
                next(stream)
                token = capture_string(stream, delimiter='"')
                path.append(token)
            case ";" | "," | "{" | "[" | "}" | "]":
                break
            case _:
                # accumulate until we have a complete word
                bare_word = capture_bare_word(stream, delimiters=list(".;,{}[]"))
                path.append(bare_word)
    return ReferenceToken(position, path, global_scope)


def tokenize(program: str) -> List[Token]:
    """First pass of the source code, transform raw text into tokens"""
    tokens: List[Token] = []
    stream: peekable[Char] = peekable(enumerate(program))

    while next_item := next(stream, None):
        position, character = next_item
        # skip whitespace
        if character.isspace():
            continue

        # separate the program into tokens by walking forward. I guess this
        # means the grammar is context-free?
        match character:
            case ";" | ",":
                tokens.append(SymbolToken(position, Symbol.end_of_statement))
            case "{":
                tokens.append(SymbolToken(position, Symbol.left_curly_brace))
            case "}":
                tokens.append(SymbolToken(position, Symbol.right_curly_brace))
            case "[":
                tokens.append(SymbolToken(position, Symbol.left_square_bracket))
            case "]":
                tokens.append(SymbolToken(position, Symbol.right_square_bracket))
            case "=" | ":":
                tokens.append(SymbolToken(position, Symbol.assignment))
            case '"':
                token = capture_string(stream, delimiter='"')
                tokens.append(LiteralToken(position, "".join(token)))
            case "`":
                token = capture_string(stream, delimiter="`")
                tokens.append(InterpolationToken(position, token))
            case "&":
                reference = parse_reference(stream)
                tokens.append(reference)
            case _:
                bare_word = capture_bare_word(stream, first=character, delimiters=[" ", ":", "]", ",", ";", "}"])
                tokens.append(BareWord(position, bare_word))

    return tokens
