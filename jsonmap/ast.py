"""
Turns tokenized input into an abstract syntax tree which can then be interpreted
and executed
"""


from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from functools import reduce
import operator
from pprint import pprint
from typing import Any, Dict, List, Optional, Tuple, Type, TypeVar

from more_itertools import peekable
from jsonmap import data
from jsonmap.error import JsonMapSyntaxError
from jsonmap.data import Json

from jsonmap.tokens import BareWord, ListIndexReferenceToken, ReferenceToken, Symbol, SymbolToken, LiteralToken, Token


def collate(
    source: Array | Reference, scope: Json, universe: Optional[Json] = None
) -> List[Any] | Dict[str | int, Any]:
    """
    Resolves all references which are required as part of the argument to a
    function
    """
    match source:
        case Array():
            to_map = source.evaluate(scope, universe)
        case Reference():
            to_map = data.resolve(source.path, scope)
    # check to make sure we have a list-like object
    if not isinstance(to_map, (list, dict)):
        raise ValueError('The argument to "map" must be iterable')
    return to_map


@dataclass(frozen=True)  # type: ignore # this will be cleaned up when 3.11  comes out...
class AstNode(ABC):
    """base class for all abstract syntax tree elements"""

    position: int

    @staticmethod
    @abstractmethod
    def parse(tokens: peekable[Token]) -> AstNode:
        """
        Consume from the stream of tokens and construct the next node in the
        tree
        """


@dataclass(frozen=True)
class Lhs(AstNode):
    """The left-hand side of a statement"""

    value: str

    @staticmethod
    def parse(tokens: peekable[Token]) -> Lhs:
        # no-ops are legal, so we have to loop through them
        match token := next(tokens):
            case BareWord(pos, value) | LiteralToken(pos, value):
                return Lhs(pos, value)
            case SymbolToken(pos, symbol=Symbol.end_of_statement):
                return NoOpLhs(pos, "")
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
class AnonymousLhs(Lhs):
    """A left hand side with no name"""


class Rhs(AstNode, ABC):
    """The right-hand side of the assignment expression"""

    @staticmethod
    def _assert_end_of_statement(tokens: peekable[Token], collection_argument: bool = False) -> None:
        if collection_argument:
            return
        if (token := tokens.peek()).is_symbol(Symbol.right_curly_brace) or token.is_symbol(Symbol.right_square_bracket):
            return
        if not (token := next(tokens)).is_symbol(Symbol.end_of_statement):
            raise JsonMapSyntaxError(token.position, "Expected end-of-statement symbol (semicolon or comma)")

    @staticmethod
    def parse(tokens: peekable[Token], *, collection_argument: bool = False) -> Rhs:
        match token := next(tokens):
            case LiteralToken():
                Rhs._assert_end_of_statement(tokens)
                return ValueLiteral.new(token)
            case ListIndexReferenceToken():
                Rhs._assert_end_of_statement(tokens, collection_argument)
                return ListIndexReference.new(token)
            case ReferenceToken():
                Rhs._assert_end_of_statement(tokens, collection_argument)
                return Reference.new(token)
            case SymbolToken(position, symbol=Symbol.left_curly_brace):
                return Scope.parse(tokens, position=position)
            case BareWord(position, value="null"):
                Rhs._assert_end_of_statement(tokens)
                return NoOpRhs(position)
            case BareWord(position, value):
                if (parsed := NumericLiteral.parse_float(value)) is not None:
                    return NumericLiteral(position, parsed)
                return CollectionOperation.parse(tokens, position=position, keyword=value)
            case SymbolToken(position, symbol=Symbol.left_square_bracket):
                return Array.parse(tokens)
            case _:
                raise JsonMapSyntaxError(token.position, f"Invalid right-hand side: {token}")

    @abstractmethod
    def evaluate(self, scope: Json, universe: Optional[Json] = None) -> Json:
        """
        Fetch the value of the mapped data from the input JSON
        """


@dataclass(frozen=True)
class NoOpRhs(Rhs):
    """No-op right hand side"""

    def evaluate(self, scope: Json, universe: Optional[Json] = None) -> Json:
        return None


@dataclass(frozen=True)
class ValueLiteral(Rhs):
    """A non-object value (no calculation required)"""

    value: str

    @staticmethod
    def new(val: LiteralToken) -> ValueLiteral:
        """instantiate the value literal from its corresponding token"""
        return ValueLiteral(val.position, val.text)

    def evaluate(self, scope: Json, universe: Optional[Json] = None) -> Json:
        return self.value


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

    def evaluate(self, scope: Json, universe: Optional[Json] = None) -> Json:
        return self.value


@dataclass(frozen=True)
class ObjectLiteral(Rhs):
    """An embedded JSON object"""

    tokens: List[str]

    def evaluate(self, scope: Json, universe: Optional[Json] = None) -> Json:
        return None


R = TypeVar("R", bound="Reference")


@dataclass(frozen=True)
class Reference(Rhs):
    """A reference to an existing field in the input JSON"""

    path: List[str | int]
    global_scope: bool

    @classmethod
    def new(cls: Type[R], ref: ReferenceToken) -> R:
        """instantiate a reference from its corresponding token"""
        return cls(ref.position, ref.path, ref.global_scope)

    def evaluate(self, scope: Json, universe: Optional[Json] = None) -> Json:
        if self.global_scope:
            return data.resolve(self.path, universe)
        return data.resolve(self.path, scope)


@dataclass(frozen=True)
class ListIndexReference(Reference):
    """
    When using a collection operation on a list of anonymous values (e.g. map
    over an array of Numbers) we need a way to reference which positional
    argument a value came from.
    """


@dataclass(frozen=True)
class Scope(Rhs):
    """A collection of statements within an interior namespace"""

    # single statement scopes are anonymous
    contents: Statement | List[Statement]

    @staticmethod
    def parse(tokens: peekable[Token], *, collection_argument: bool = False, position: int = 0) -> Scope:
        # parse the inner scope contents
        statements = assemble(tokens, inner_scope=True)
        return Scope(position, statements)

    def evaluate(self, scope: Json, universe: Optional[Json] = None) -> Json:
        match self.contents:
            case list():
                return dict(
                    result for statement in self.contents if (result := statement.evaluate(scope, universe)) is not None
                )
            case Statement():
                if result := self.contents.evaluate(scope, universe):
                    _, value = result
                    return value
                raise ValueError("Illegal statement evaluation")
            case _:
                raise ValueError("Illegal scope type")


@dataclass(frozen=True)
class Array(Rhs):
    """An ordered list of values with fixed size"""

    values: List[Rhs]

    @staticmethod
    def parse(tokens: peekable[Token], *, collection_argument: bool = False) -> Array:
        values = []
        position = tokens.peek().position
        while not tokens.peek().is_symbol(Symbol.right_square_bracket):
            values.append(Rhs.parse(tokens))
            if tokens.peek().is_symbol(Symbol.end_of_statement):
                next(tokens)  # skip commas in a list
        next(tokens)  # pop the right square bracket before returning
        return Array(position, values)

    def evaluate(self, scope: Json, universe: Optional[Json] = None) -> Json:
        return [rhs.evaluate(scope, universe) for rhs in self.values]


@dataclass(frozen=True)
class CollectionOperation(Scope):
    """
    A "collection operation" in this context means any action which is meant to
    operate on a list-like JSON object, such as mapping list values or
    performing a reduce or fold.
    """

    @staticmethod
    def parse(
        tokens: peekable[Token], *, position: int = 0, keyword: str = "", collection_argument: bool = False
    ) -> CollectionOperation:
        match keyword:
            case "bind":
                return Bind.parse(tokens, position=position)
            case "map":
                return Map.parse(tokens, position=position)
            case "zip":
                return Zip.parse(tokens, position=position)
            case _:
                raise JsonMapSyntaxError(position, f'Unrecognized keyword "{keyword}"')


@dataclass(frozen=True)
class Bind(CollectionOperation):
    """binds a namespace for shorter reference paths"""

    reference: Reference

    @staticmethod
    def parse(
        tokens: peekable[Token], *, position: int = 0, keyword: str = "", collection_argument: bool = False
    ) -> CollectionOperation:
        # after we parse the keyword, we expect an RHS with no end-of-statement
        # symbol followed by a scope
        reference = Rhs.parse(tokens, collection_argument=True)
        match reference:
            case Reference():
                pass
            case _:
                raise JsonMapSyntaxError(position, f"Unsupported argument for bind {reference}")
        # we then expect an inner scope
        if not (token := tokens.peek()).is_symbol(Symbol.left_curly_brace):
            raise JsonMapSyntaxError(token.position, 'expected start of an inner scope "{"')
        next(tokens)
        # parse the inner scope
        statements = Scope.parse(tokens, position=tokens.peek().position)
        return Bind(position, statements.contents, reference)

    def evaluate(self, scope: Json, universe: Optional[Json] = None) -> Json:
        narrowed_scope = data.resolve(self.reference.path, scope)
        match narrowed_scope:
            case dict():
                return super().evaluate(narrowed_scope, universe)
            case _:
                raise ValueError(
                    "The reference passed as an argument to bind must resolve to a JSON object. "
                    f'The reference path {self.reference} instead resolved to "{narrowed_scope}"'
                )


@dataclass(frozen=True)
class Map(CollectionOperation):
    """A transformation over every item in a collection"""

    source: Array | Reference

    @staticmethod
    def parse(
        tokens: peekable[Token], *, position: int = 0, keyword: str = "", collection_argument: bool = False
    ) -> CollectionOperation:
        # after we parse the keyword, we expect an RHS with no end-of-statement
        # symbol followed by a scope
        source = Rhs.parse(tokens, collection_argument=True)
        match source:
            case Array() | Reference():
                pass
            case _:
                raise JsonMapSyntaxError(position, f"Unsupported argument for map {source}")
        match tokens.peek():
            case SymbolToken(symbol=Symbol.left_curly_brace):
                next(tokens)
                statements = Scope.parse(tokens, position=tokens.peek().position).contents
            case SymbolToken(position, symbol=Symbol.left_square_bracket):
                next(tokens)
                array = Array.parse(tokens).values
                if len(array) != 1:
                    raise ValueError("Only one entry is allowed in the anonymous map scope")
                statements = Statement(AnonymousLhs(position, ""), array[0])
        # parse the inner scope
        # statements = Scope.parse(tokens, position=tokens.peek().position)
        return Map(position, statements, source)

    def evaluate(self, scope: Json, universe: Optional[Json] = None) -> Json:
        return [super(Map, self).evaluate(item, universe) for item in collate(self.source, scope, universe)]


@dataclass(frozen=True)
class Zip(CollectionOperation):
    """Iterate pairwise over a number of distinct collections"""

    sources: List[Array | Reference]

    @staticmethod
    def _parse_zip_args(tokens: peekable[Token], position: int) -> List[Array | Reference]:
        sources = []
        while not tokens.peek().is_symbol(Symbol.left_curly_brace):
            source = Rhs.parse(tokens, collection_argument=True)
            match source:
                case Array() | Reference():
                    sources.append(source)
                case _:
                    raise JsonMapSyntaxError(position, "Invalid argument for zip")
        return sources

    @staticmethod
    def parse(
        tokens: peekable[Token], *, position: int = 0, keyword: str = "", collection_argument: bool = False
    ) -> CollectionOperation:
        sources = Zip._parse_zip_args(tokens, position)
        # in order for the above statement to return, it would have had to have
        # been a left curly brace
        next(tokens)
        # parse the inner scope
        statements = Scope.parse(tokens, position=tokens.peek().position)
        return Zip(position, statements.contents, sources)

    def evaluate(self, scope: Json, universe: Optional[Json] = None) -> Json:
        resolved = [collate(source, scope, universe) for source in self.sources]
        # if we have a list of non-object values (ints, strings, etc.) then we
        # turn them into dictionaries with the position of the zip argument they
        # came from as the index. This will not cause a naming conflict because
        # JSON keys can only be strings, where these newly-inserted keys will
        # always be integers. Is it a bit of a hack? Yes. It is. Oh well...
        indexed = []
        for index, arg_list in enumerate(resolved):
            if all(isinstance(arg, dict) for arg in arg_list):
                indexed.append(arg_list)
            else:
                deanonymized = [{index: arg} for arg in arg_list]
                indexed.append(deanonymized)

        zipped = zip(*indexed)
        merged_scopes: List[Dict[str | int, Json]] = [reduce(operator.ior, scopes, {}) for scopes in zipped]
        return [super(Zip, self).evaluate(zipped_scope, universe) for zipped_scope in merged_scopes]


ScopeEntry = Tuple[str, Json]


@dataclass(frozen=True)
class Statement:
    """A self-contained unit of evaluation"""

    lhs: Lhs
    rhs: Rhs

    def evaluate(self, scope: Json, universe: Optional[Json] = None) -> Optional[ScopeEntry]:
        """
        Apply the mapping from the source json to the new value for the given
        instruction
        """
        match self.lhs:
            case NoOpLhs():
                return None
            case AnonymousLhs():
                key = ""  # this is a placeholder to satisfy our type system
            case _:
                key = self.lhs.value

        # evaluate the right-hand-side
        value = self.rhs.evaluate(scope, universe)
        return (key, value)


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
