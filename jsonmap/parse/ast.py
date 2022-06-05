from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Iterator, List, Optional

from jsonmap.parse.tokens import BareWord, ReferenceToken, Symbol, SymbolToken, LiteralToken, Token


@dataclass(frozen=True)  # type: ignore # this will be cleaned up when 3.11  comes out...
class AstNode(ABC):
    """base class for all abstract syntax tree elements"""

    position: int

    @staticmethod
    @abstractmethod
    def parse(tokens: Iterator[Token], **kwargs: str) -> AstNode:
        """
        Consume from the stream of tokens and construct the next node in the
        tree
        """


@dataclass(frozen=True)
class Lhs(AstNode):
    value: str

    @staticmethod
    def parse(tokens: Iterator[Token], **kwargs: str) -> Lhs:
        match token := next(tokens):
            case BareWord(pos, value) | LiteralToken(pos, value):
                return Lhs(pos, value)
            case _:
                raise ValueError(f"Invalid Lhs at position {token.position}")


@dataclass(frozen=True)
class Rhs(AstNode, ABC):
    """The right-hand side of the assignment expression"""

    @staticmethod
    def parse(tokens: Iterator[Token], **kwargs: str) -> Rhs:
        match token := next(tokens):
            case LiteralToken():
                return ValueLiteral.new(token)
            case ReferenceToken():
                return Reference.new(token)
            case BareWord(pos, value):
                return CollectionOperation.parse(tokens, keyword=value, position=token.position)  # type: ignore
            case _:
                raise ValueError(f"Invalid RHS at position {token.position}")


@dataclass(frozen=True)
class ValueLiteral(Rhs):
    """A non-object value (no calculation required)"""

    value: str

    @staticmethod
    def new(val: LiteralToken) -> ValueLiteral:
        return ValueLiteral(val.position, val.text)


@dataclass(frozen=True)
class ObjectLiteral(Rhs):
    """An embedded JSON object"""

    tokens: List[str]


@dataclass(frozen=True)
class Reference(Rhs):
    """A reference to an existing field in the input JSON"""

    path: List[str]
    global_scope: bool

    @staticmethod
    def new(ref: ReferenceToken) -> Reference:
        return Reference(ref.position, ref.path, ref.global_scope)


@dataclass(frozen=True)
class Scope(Rhs):
    statements: List[Statement]


@dataclass(frozen=True)
class Array(Rhs):
    values: List[Rhs]


@dataclass(frozen=True)
class CollectionOperation(Scope):
    """
    A "collection operation" in this context means any action which is meant to
    operate on a list-like JSON object, such as mapping list values or
    performing a reduce or fold.
    """

    @staticmethod
    def parse(tokens: Iterator[Token], **kwargs: str) -> CollectionOperation:
        match kwargs["keyword"]:
            case "map":
                return Map.parse(tokens)
            case "zip":
                return Zip.parse(tokens)
            case _:
                raise ValueError(f"Unrecognized keyword at position {kwargs['position']}")


@dataclass(frozen=True)
class Map(CollectionOperation):
    source: Array

    @staticmethod
    def parse(tokens: Iterator[Token], **kwargs: str) -> CollectionOperation:
        pass


@dataclass(frozen=True)
class Zip(CollectionOperation):
    sources: List[Array]

    @staticmethod
    def parse(tokens: Iterator[Token], **kwargs: str) -> CollectionOperation:
        pass


@dataclass(frozen=True)
class Statement:
    lhs: Lhs
    rhs: Rhs


def assemble(tokens: List[Token]) -> List[Statement]:
    """Transform the tokenized input into an executable abstract syntax tree"""

    stream = iter(tokens)
    statements: List[Statement] = []

    while statement := consume_statement(stream):
        statements.append(statement)

    return statements


def consume_statement(stream: Iterator[Token]) -> Optional[Statement]:
    """Consume a single statement from the token stream"""
    try:
        return _consume_statement(stream)
    except StopIteration:
        return None


def _consume_statement(stream: Iterator[Token]) -> Statement:
    # get the name we will be binding the RHS to
    lhs = Lhs.parse(stream)

    # make sure we have an assignment operator
    if not (token := next(stream)).is_symbol(Symbol.assignment):
        print(token)
        raise ValueError(f"Missing assignment operator at position {token.position}")

    # now get the right-hand side
    rhs = Rhs.parse(stream)

    # make sure it ends in a semicolon
    if not (token := next(stream)).is_symbol(Symbol.semicolon):
        raise ValueError(f"Missing semicolon at position {token.position}")

    return Statement(lhs, rhs)
