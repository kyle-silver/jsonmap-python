"""
Transform raw source input into a token stream which can then be assembled into
an abstract syntax tree
"""

from __future__ import annotations

from abc import ABC
from dataclasses import dataclass
from enum import IntEnum, auto
import itertools
from typing import List, Optional, Tuple

from more_itertools import peekable

from jsonmap.error import InvalidEscapeSequence, JsonMapSyntaxError


# just for the ease of reading type signatures
Char = Tuple[int, str]

ESCAPED_CHARS = {
    "b": "\b",
    "f": "\f",
    "n": "\n",
    "r": "\r",
    "t": "\t",
    '"': '"',
    "\\": "\\",
}


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

    path: List[str | int]
    global_scope: bool = False


@dataclass(frozen=True)
class ListIndexReferenceToken(ReferenceToken):
    """References an item's position in a list rather than its field name"""


def _capture_escaped_hex_value(stream: peekable[Char], length: int) -> str:
    """Capture the numeric hex value of a sequence like \xAB or \uABCD"""
    hex_code = "".join(str(x) for _, x in itertools.islice(stream, length))
    hex_value = int(hex_code, 16)
    return chr(hex_value)


def capture_string(stream: peekable[Char], delimiter: str) -> str:
    """
    Walk through the iterable and pull out a string literal sequence from the
    source code.
    """
    token = []
    while (item := next(stream))[1] != delimiter:
        pos, char = item
        if char != "\\":
            token.append(char)
            continue
        _, escape_code = next(stream)
        if escaped := ESCAPED_CHARS.get(escape_code):
            token.append(escaped)
        elif escape_code == "x":
            hex_code = _capture_escaped_hex_value(stream, length=2)
            token.append(hex_code)
        elif escape_code == "u":
            hex_code = _capture_escaped_hex_value(stream, length=4)
            token.append(hex_code)
        else:
            # token.append(escape_code)
            raise InvalidEscapeSequence(pos, escape_code)
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
    path: List[str | int] = []
    global_scope = False
    position = None
    is_list_index = False
    while item := stream.peek():
        current_position, next_char = item
        if position is None:
            position = current_position  # only assign this once, the first time
        if next_char.isspace():
            break
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
            case "?":
                next(stream)
                is_list_index = True
            case ";" | "," | "{" | "[" | "}" | "]":
                break
            case _:
                # accumulate until we have a complete word
                bare_word = capture_bare_word(stream, delimiters=[".", ";", ",", "{", "}", "[", "]", "]", " "])
                if is_list_index:
                    path.append(int(bare_word))
                else:
                    path.append(bare_word)
    if is_list_index:
        return ListIndexReferenceToken(position, path, global_scope)
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
