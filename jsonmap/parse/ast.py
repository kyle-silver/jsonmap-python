from abc import ABC
from dataclasses import dataclass
from enum import Enum, auto
from typing import List


@dataclass
class Lhs:
    value: str


@dataclass
class Rhs(ABC):
    pass


class Assignment(Enum):
    equals = auto()
    walrus = auto()


@dataclass
class Statement:
    lhs: Lhs
    rhs: Rhs
    assignment: Assignment


@dataclass
class Scope:
    statements: List[Statement]


@dataclass
class Array(Rhs):
    values: List[Rhs]


@dataclass
class Loop(ABC):
    statements: List[Statement]


@dataclass
class ForEach(Loop):
    source: Array


@dataclass
class Zip(Loop):
    sources: List[Array]
