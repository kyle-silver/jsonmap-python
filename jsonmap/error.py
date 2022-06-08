"""
For error handling when parsing a program
"""
from __future__ import annotations


from typing import NamedTuple


class JsonMapSyntaxError(Exception):
    """For errors in creating an executable program from the source document"""

    def __init__(self, position: int, *args: object) -> None:
        self.position = position
        super().__init__(*args)


SyntaxErrorDebugInfo = NamedTuple(
    "SyntaxErrorDebugInfo", [("line", int), ("column", int), ("error", JsonMapSyntaxError)]
)


def get_error_position(error: JsonMapSyntaxError, program: str) -> SyntaxErrorDebugInfo:
    """Get the position in the source code of the error"""
    line = 1
    column = 0
    position = error.position
    stream = iter(program)
    while position > 0:
        if next(stream) == "\n":
            column = 0
            line += 1
        else:
            column += 1
        position -= 1
    return SyntaxErrorDebugInfo(line, column, error)


def display_error(debug: SyntaxErrorDebugInfo, _program: str) -> None:
    """print a helpful error message"""
    print(f"Syntax error at line {debug.line} and column {debug.column}: {debug.error}")


def handle(error: JsonMapSyntaxError, program: str) -> None:
    """handle parsing errors"""
    debug = get_error_position(error, program)
    display_error(debug, program)
