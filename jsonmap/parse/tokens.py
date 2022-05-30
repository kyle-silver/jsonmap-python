from dataclasses import dataclass
from enum import Enum, auto
from typing import List


class Category(Enum):
    semicolon = auto()
    assignment = auto()
    bracket = auto()
    reference = auto()
    text = auto()
    interpolation = auto()


@dataclass(frozen=True)
class Token:
    value: str
    category: Category


def tokenize(program: str) -> List[Token]:
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
                token = []
                token.append('"')
                while (next_char := next(stream)) != '"':
                    token.append(next_char)
                token.append('"')
                tokens.append(Token("".join(token), Category.text))
            case _:
                token = []
                token.append(character)
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
