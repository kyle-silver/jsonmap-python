from __future__ import annotations


from abc import ABC, abstractclassmethod, abstractmethod
from dataclasses import dataclass
from typing import Iterator, List, Optional, Type, TypeVar
from typing_extensions import Self

from jsonmap.parse.tokens import BareWord, ReferenceToken, Symbol, SymbolToken, LiteralToken, Token


# type variable for the AST node
T = TypeVar("T", bound="AstNode")
L = TypeVar("L", bound="Lhs")
R = TypeVar("R", bound="Rhs")


@dataclass(frozen=True)
class AstNode(ABC):
    """base class for all abstract syntax tree elements"""

    @classmethod
    @abstractclassmethod
    def parse(cls: Type[T], tokens: Iterator[Token]) -> T:
        """
        Consume from the stream of tokens and construct the next node in the
        tree
        """


@dataclass(frozen=True)
class Lhs:
    value: str

    @classmethod
    def parse(cls: Type[L], tokens: Iterator[Token]) -> L:
        match next(tokens, None):
            case BareWord(value):
                return cls(value)
            case _:
                raise ValueError("Invalid Lhs")


@dataclass(frozen=True)
class Rhs(AstNode, ABC):
    """The right-hand side of the assignment expression"""

    @classmethod
    def parse(cls: Type[R], tokens: Iterator[Token]) -> R:  # change this to typing.Self once 3.11 comes out...
        match (next_token := next(tokens)):
            case LiteralToken(text):
                return ValueLiteral(value=text)  # type: ignore
            case ReferenceToken(path, global_scope):
                return Reference(path, global_scope)  # type: ignore
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
class Loop(Scope):
    pass


@dataclass(frozen=True)
class Map(Loop):
    source: Array


@dataclass(frozen=True)
class Zip(Loop):
    sources: List[Array]


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
