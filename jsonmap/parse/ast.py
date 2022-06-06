from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Iterator, List, Optional

from more_itertools import peekable
from jsonmap.parse.error import JsonMapSyntaxError

from jsonmap.parse.tokens import BareWord, ReferenceToken, Symbol, SymbolToken, LiteralToken, Token


@dataclass(frozen=True)  # type: ignore # this will be cleaned up when 3.11  comes out...
class AstNode(ABC):
    """base class for all abstract syntax tree elements"""

    position: int

    @staticmethod
    @abstractmethod
    def parse(tokens: peekable[Token], **kwargs: str) -> AstNode:
        """
        Consume from the stream of tokens and construct the next node in the
        tree
        """


@dataclass(frozen=True)
class Lhs(AstNode):
    value: str

    @staticmethod
    def parse(tokens: peekable[Token], **kwargs: str) -> Lhs:
        # no-ops are legal, so we have to loop through them
        match token := next(tokens):
            case BareWord(pos, value) | LiteralToken(pos, value):
                return Lhs(pos, value)
            case _:
                raise JsonMapSyntaxError(token.position, f"Invalid start to expression: {token}")


@dataclass(frozen=True)
class Rhs(AstNode, ABC):
    """The right-hand side of the assignment expression"""

    @staticmethod
    def _assert_end_of_statement(tokens: Iterator[Token]) -> None:
        if not (token := next(tokens)).is_symbol(Symbol.end_of_statement):
            raise JsonMapSyntaxError(token.position, f"Expected end-of-statement symbol (semicolon or comma)")

    @staticmethod
    def parse(tokens: peekable[Token], **kwargs: str) -> Rhs:
        match token := next(tokens):
            case LiteralToken():
                Rhs._assert_end_of_statement(tokens)
                return ValueLiteral.new(token)
            case ReferenceToken():
                Rhs._assert_end_of_statement(tokens)
                return Reference.new(token)
            case SymbolToken(position, symbol=Symbol.left_curly_brace):
                return Scope.parse(tokens, position=position)  # type: ignore
            case BareWord(position, value):
                return CollectionOperation.parse(tokens, position=position, keyword=value)  # type: ignore
            case _:
                raise JsonMapSyntaxError(token.position, f"Invalid right-hand side: {token}")


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

    @staticmethod
    def parse(tokens: peekable[Token], **kwargs: str) -> Scope:
        # parse the inner scope contents
        statements = assemble(tokens, inner_scope=True)
        return Scope(kwargs["position"], statements)  # type: ignore


@dataclass(frozen=True)
class Array(Rhs):
    values: List[Rhs]

    @staticmethod
    def parse(tokens: peekable[Token], **kwargs: str) -> Array:
        values = []
        position = tokens.peek().position
        while not tokens.peek().is_symbol(Symbol.left_square_bracket):
            values.append(Rhs.parse(tokens))
        return Array(position, values)


@dataclass(frozen=True)
class CollectionOperation(Scope):
    """
    A "collection operation" in this context means any action which is meant to
    operate on a list-like JSON object, such as mapping list values or
    performing a reduce or fold.
    """

    @staticmethod
    def parse(tokens: peekable[Token], **kwargs: str) -> CollectionOperation:
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
    def parse(tokens: peekable[Token], **kwargs: str) -> CollectionOperation:
        pass


@dataclass(frozen=True)
class Zip(CollectionOperation):
    sources: List[Array]

    @staticmethod
    def parse(tokens: peekable[Token], **kwargs: str) -> CollectionOperation:
        pass


@dataclass(frozen=True)
class Statement:
    lhs: Lhs
    rhs: Rhs


def assemble(stream: peekable[Token], inner_scope: bool = False) -> List[Statement]:
    """Transform the tokenized input into an executable abstract syntax tree"""
    statements: List[Statement] = []

    while statement := consume_statement(stream, inner_scope=inner_scope):
        statements.append(statement)

    return statements


def consume_statement(stream: peekable[Token], inner_scope: bool = False) -> Optional[Statement]:
    """Consume a single statement from the token stream"""
    try:
        return _consume_statement(stream, inner_scope=inner_scope)
    except StopIteration:
        return None


def _consume_statement(stream: peekable[Token], inner_scope: bool = False) -> Statement:
    # if we reach the end of a scope, send a signal
    if (token := stream.peek()).is_symbol(Symbol.right_curly_brace):
        if inner_scope:
            next(stream)  # pop the curly brace
            raise StopIteration()
        raise JsonMapSyntaxError(token.position, 'Encountered unexpected end to scope "}}"')

    # get the name we will be binding the RHS to
    lhs = Lhs.parse(stream)

    # make sure we have an assignment operator
    if not (token := next(stream)).is_symbol(Symbol.assignment):
        print(token)
        raise JsonMapSyntaxError(token.position, "Expected assignment operator (either equals or colon)")

    # now get the right-hand side
    rhs = Rhs.parse(stream)

    return Statement(lhs, rhs)
