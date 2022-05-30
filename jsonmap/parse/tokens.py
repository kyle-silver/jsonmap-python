from dataclasses import dataclass
from enum import Enum, auto
from typing import Iterable, List


# pylint: disable=invalid-name
class Category(Enum):
    """
    The different categories of tokens, which we will later assemble into the
    AST
    """

    semicolon = auto()
    assignment = auto()
    bracket = auto()
    reference = auto()
    text = auto()
    interpolation = auto()


@dataclass(frozen=True)
class Token:
    """Represents a single AST token"""

    value: str
    category: Category


def capture_string(stream: Iterable[str], delimiter: str) -> str:
    """
    Walk through the iterable and pull out a string literal sequence from the
    source code.
    """
    token = []
    while (next_char := next(stream)) != delimiter:
        token.append(next_char)
    return "".join(token)


def tokenize(program: str) -> List[Token]:
    """First pass of the source code, transform raw text into tokens"""
    tokens = []
    stream = iter(program)

    while character := next(stream, None):
        # skip whitespace
        if character.isspace():
            continue

        # separate the program into tokens by walking forward. I guess this
        # means the grammar is context-free?
        match character:
            case ";":
                # semicolons terminate statements
                tokens.append(Token(character, Category.semicolon))
            case "{" | "}" | "[" | "]":
                tokens.append(Token(character, Category.bracket))
            case "=":
                tokens.append(Token(character, Category.assignment))
            case ":":
                if next(stream) == "=":
                    tokens.append(Token(":=", Category.assignment))
                else:
                    raise TypeError("Invalid symbol")
            case '"':
                # if it's a string, read forward until we've reached the end of
                # the string.
                token = capture_string(stream, '"')
                tokens.append(Token("".join(token), Category.text))
            case "`":
                token = capture_string(stream, "`")
                tokens.append(Token(token, Category.interpolation))
            case _:
                token = []  # type: ignore (this is due to a bug in mypy)
                token.append(character)  # type: ignore (this is due to a bug in mypy)
                found_semicolon = False
                while (next_char := next(stream)).isspace() is not True:
                    if next_char == ";":
                        found_semicolon = True
                        break
                    token.append(next_char)
                tokens.append(Token("".join(token), Category.reference))
                if found_semicolon:
                    tokens.append(Token(";", Category.semicolon))
    return tokens
