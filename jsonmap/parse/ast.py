"""
Turns tokenized input into an abstract syntax tree which can then be interpreted
and executed
"""


from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Optional

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
    """The left-hand side of a statement"""

    value: str

    @staticmethod
    def parse(tokens: peekable[Token], **kwargs: str) -> Lhs:
        # no-ops are legal, so we have to loop through them
        match token := next(tokens):
            case BareWord(pos, value) | LiteralToken(pos, value):
                return Lhs(pos, value)
            case SymbolToken(pos, symbol=Symbol.end_of_statement):
                return NoOpLhs(pos, "\0")
            case _:
                raise JsonMapSyntaxError(token.position, f"Invalid start to expression: {token}")

    def noop(self) -> bool:
        """Indicates if the LHS is a no-op"""
        return False


@dataclass(frozen=True)
class NoOpLhs(Lhs):
    """No-op left hand side"""

    def noop(self) -> bool:
        return True


@dataclass(frozen=True)
class Rhs(AstNode, ABC):
    """The right-hand side of the assignment expression"""

    @staticmethod
    def _assert_end_of_statement(tokens: peekable[Token]) -> None:
        if (token := tokens.peek()).is_symbol(Symbol.right_curly_brace) or token.is_symbol(Symbol.right_square_bracket):
            return
        if not (token := next(tokens)).is_symbol(Symbol.end_of_statement):
            raise JsonMapSyntaxError(token.position, "Expected end-of-statement symbol (semicolon or comma)")

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
                if parsed := NumericLiteral.parse_float(value):
                    return NumericLiteral(position, parsed)
                return CollectionOperation.parse(tokens, position=position, keyword=value)  # type: ignore
            case SymbolToken(position, symbol=Symbol.left_square_bracket):
                return Array.parse(tokens)
            case _:
                raise JsonMapSyntaxError(token.position, f"Invalid right-hand side: {token}")


@dataclass(frozen=True)
class NoOpRhs(Rhs):
    """No-op right hand side"""


@dataclass(frozen=True)
class ValueLiteral(Rhs):
    """A non-object value (no calculation required)"""

    value: str

    @staticmethod
    def new(val: LiteralToken) -> ValueLiteral:
        """instantiate the value literal from its corresponding token"""
        return ValueLiteral(val.position, val.text)


@dataclass(frozen=True)
class NumericLiteral(Rhs):
    """A numeric value"""

    value: float

    @staticmethod
    def parse_float(value: str) -> Optional[float]:
        """
        attempt to parse a floating point number as a valid numeric literal
        """
        try:
            return float(value)
        except ValueError:
            return None


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
        """instantiate a reference from its corresponding token"""
        return Reference(ref.position, ref.path, ref.global_scope)


@dataclass(frozen=True)
class Scope(Rhs):
    """A collection of statements within an interior namespace"""

    statements: List[Statement]

    @staticmethod
    def parse(tokens: peekable[Token], **kwargs: str) -> Scope:
        # parse the inner scope contents
        statements = assemble(tokens, inner_scope=True)
        return Scope(kwargs["position"], statements)  # type: ignore


@dataclass(frozen=True)
class Array(Rhs):
    """An ordered list of values with fixed size"""

    values: List[Rhs]

    @staticmethod
    def parse(tokens: peekable[Token], **kwargs: str) -> Array:
        values = []
        position = tokens.peek().position
        while not tokens.peek().is_symbol(Symbol.right_square_bracket):
            values.append(Rhs.parse(tokens))
            if tokens.peek().is_symbol(Symbol.end_of_statement):
                next(tokens)  # skip commas in a list
        next(tokens)  # pop the right square bracket before returning
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
        match bare_word := kwargs["keyword"]:
            case "map":
                return Map.parse(tokens)
            case "zip":
                return Zip.parse(tokens)
            case _:
                if bare_word.isnumeric():  # this is kinda... not great...?
                    return NumericLiteral(kwargs["position"], float(bare_word))  # type: ignore
                raise ValueError(f"Unrecognized keyword at position {kwargs['position']}")


@dataclass(frozen=True)
class Map(CollectionOperation):
    """A transformation over every item in a collection"""

    source: Array

    @staticmethod
    def parse(tokens: peekable[Token], **kwargs: str) -> CollectionOperation:
        pass


@dataclass(frozen=True)
class Zip(CollectionOperation):
    """Iterate pairwise over a number of distinct collections"""

    sources: List[Array]

    @staticmethod
    def parse(tokens: peekable[Token], **kwargs: str) -> CollectionOperation:
        pass


@dataclass(frozen=True)
class Statement:
    """A self-contained unit of evaluation"""

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

    # check for no-op
    if lhs.noop():
        return Statement(lhs, NoOpRhs(lhs.position))

    # make sure we have an assignment operator
    if not (token := next(stream)).is_symbol(Symbol.assignment):
        raise JsonMapSyntaxError(token.position, "Expected assignment operator (either equals or colon)")

    # now get the right-hand side
    rhs = Rhs.parse(stream)

    return Statement(lhs, rhs)
