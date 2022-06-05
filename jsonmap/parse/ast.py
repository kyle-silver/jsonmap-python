from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Iterator, List, Optional

from jsonmap.parse.tokens import BareWord, ReferenceToken, Symbol, SymbolToken, LiteralToken, Token


class AstNode(ABC):
    """base class for all abstract syntax tree elements"""

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
        match next(tokens, None):
            case BareWord(value):
                return Lhs(value)
            case _:
                raise ValueError("Invalid Lhs")


@dataclass(frozen=True)
class Rhs(AstNode, ABC):
    """The right-hand side of the assignment expression"""

    @staticmethod
    def parse(tokens: Iterator[Token], **kwargs: str) -> Rhs:
        match next(tokens):
            case LiteralToken(text):
                return ValueLiteral(value=text)
            case ReferenceToken(path, global_scope):
                return Reference(path, global_scope)
            case BareWord(value):
                return CollectionOperation.parse(tokens, keyword=value)
            case _:
                raise ValueError("Invalid RHS")


@dataclass(frozen=True)
class ValueLiteral(Rhs):
    """A non-object value (no calculation required)"""

    value: str


@dataclass(frozen=True)
class ObjectLiteral(Rhs):
    """An embedded JSON object"""

    tokens: List[str]


@dataclass(frozen=True)
class Reference(Rhs):
    """A reference to an existing field in the input JSON"""

    path: List[str]
    global_scope: bool


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
                raise ValueError("Unrecognized loop operation")


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

    # get the name we will be binding the RHS to
    lhs = Lhs.parse(stream)

    # make sure we have an assignment operator
    match next(stream):
        case SymbolToken(symbol):
            if symbol != Symbol.assignment:
                raise ValueError("Missing assignment operator")

    # now get the right-hand side
    rhs = Rhs.parse(stream)

    return Statement(lhs, rhs)
