from abc import ABC
from dataclasses import dataclass
from enum import Enum, auto
from typing import Iterator, List, Tuple


# pylint: disable=invalid-name
class Symbol(Enum):
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


@dataclass(frozen=True)
class SymbolToken(Token):
    """Represents a language symbol"""

    symbol: Symbol


@dataclass(frozen=True)
class ReservedWord(Token):
    """Represents a language keyword"""

    value: str


@dataclass(frozen=True)
class TextToken(Token):
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


def capture_string(stream: Iterator[str], delimiter: str) -> str:
    """
    Walk through the iterable and pull out a string literal sequence from the
    source code.
    """
    token = []
    while (next_char := next(stream)) != delimiter:
        token.append(next_char)
    return "".join(token)


def capture_bare_word(stream: Iterator[str], *, starting_letter: str, delimiters: List[str]) -> Tuple[str, str]:
    token = [starting_letter]
    encountered_delimiter = None
    while next_char := next(stream):
        if next_char in delimiters:
            encountered_delimiter = next_char
            break
        token.append(next_char)
    return ("".join(token), encountered_delimiter)  # type: ignore


def parse_reference(stream: Iterator[str]) -> ReferenceToken:
    path: List[str] = []
    global_scope = False
    while next_char := next(stream):
        match next_char:
            case ".":
                continue
            case "!":
                if len(path) > 0:
                    raise ValueError('Illegal element in path "!"')
                global_scope = True
            case '"':
                token = capture_string(stream, delimiter='"')
                path.append(token)
            case _:
                # accumulate until we have a complete word
                (bare_word, delimiter) = capture_bare_word(stream, starting_letter=next_char, delimiters=[".", ";"])
                path.append(bare_word)
                if delimiter == ";":
                    break
    return ReferenceToken(path, global_scope)


def tokenize(program: str) -> List[Token]:
    """First pass of the source code, transform raw text into tokens"""
    tokens: List[Token] = []
    stream = iter(program)

    while character := next(stream, None):
        # skip whitespace
        if character.isspace():
            continue

        # separate the program into tokens by walking forward. I guess this
        # means the grammar is context-free?
        match character:
            case ";":
                tokens.append(SymbolToken(Symbol.semicolon))
            case "{":
                tokens.append(SymbolToken(Symbol.left_curly_brace))
            case "}":
                tokens.append(SymbolToken(Symbol.right_curly_brace))
            case "[":
                tokens.append(SymbolToken(Symbol.left_square_bracket))
            case "]":
                tokens.append(SymbolToken(Symbol.right_square_bracket))
            case "=":
                tokens.append(SymbolToken(Symbol.assignment))
            case '"':
                token = capture_string(stream, delimiter='"')
                tokens.append(TextToken("".join(token)))
            case "`":
                token = capture_string(stream, delimiter="`")
                tokens.append(InterpolationToken(token))
            case "&":
                reference = parse_reference(stream)
                tokens.append(reference)
                tokens.append(SymbolToken(Symbol.semicolon))
            case _:
                (bare_word, _) = capture_bare_word(stream, starting_letter=character, delimiters=[" "])
                tokens.append(ReservedWord(bare_word))

    return tokens
