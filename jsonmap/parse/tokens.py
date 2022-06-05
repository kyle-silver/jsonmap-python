from abc import ABC
from dataclasses import dataclass
from enum import Enum, IntEnum, auto
from typing import Iterator, List, NewType, Tuple

# just for ease of type signatures
CharStream = Iterator[Tuple[int, str]]


# pylint: disable=invalid-name
class Symbol(IntEnum):
    """
    The different categories of tokens, which we will later assemble into the
    AST
    """

    semicolon = auto()
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
        return isinstance(self, SymbolToken) and self.symbol == symbol


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


def capture_string(stream: CharStream, delimiter: str) -> str:
    """
    Walk through the iterable and pull out a string literal sequence from the
    source code.
    """
    token = []
    while (item := next(stream))[1] != delimiter:
        _, char = item
        token.append(char)
    return "".join(token)


def capture_bare_word(stream: CharStream, *, starting_letter: str, delimiters: List[str]) -> Tuple[str, str]:
    token = [starting_letter]
    encountered_delimiter = None
    while item := next(stream):
        _, next_char = item
        if next_char in delimiters:
            encountered_delimiter = next_char
            break
        token.append(next_char)
    return ("".join(token), encountered_delimiter)


def parse_reference(stream: CharStream) -> ReferenceToken:
    path: List[str] = []
    global_scope = False
    while item := next(stream):
        position, next_char = item
        match next_char:
            case ".":
                continue
            case "!":
                if len(path) > 0:
                    raise ValueError(f'Illegal element in path "!" at position {position}')
                global_scope = True
            case '"':
                token = capture_string(stream, delimiter='"')
                path.append(token)
            case ";":
                break
            case _:
                # accumulate until we have a complete word
                (bare_word, delimiter) = capture_bare_word(stream, starting_letter=next_char, delimiters=[".", ";"])
                path.append(bare_word)
                if delimiter == ";":
                    break
    return ReferenceToken(position, path, global_scope)


def tokenize(program: str) -> List[Token]:
    """First pass of the source code, transform raw text into tokens"""
    tokens: List[Token] = []
    stream: CharStream = enumerate(program)

    while next_item := next(stream, None):
        position, character = next_item
        # skip whitespace
        if character.isspace():
            continue

        # separate the program into tokens by walking forward. I guess this
        # means the grammar is context-free?
        match character:
            case ";":
                tokens.append(SymbolToken(position, Symbol.semicolon))
            case "{":
                tokens.append(SymbolToken(position, Symbol.left_curly_brace))
            case "}":
                tokens.append(SymbolToken(position, Symbol.right_curly_brace))
            case "[":
                tokens.append(SymbolToken(position, Symbol.left_square_bracket))
            case "]":
                tokens.append(SymbolToken(position, Symbol.right_square_bracket))
            case "=":
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
                tokens.append(SymbolToken(position, Symbol.semicolon))
            case _:
                (bare_word, _) = capture_bare_word(stream, starting_letter=character, delimiters=[" "])
                tokens.append(BareWord(position, bare_word))

    return tokens
