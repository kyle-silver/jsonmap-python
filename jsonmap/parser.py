"""
Parse program source code into something executable
"""
from __future__ import annotations

from dataclasses import dataclass
import traceback
from typing import Dict, List

from more_itertools import peekable
from jsonmap import tokens, ast, error
from jsonmap.error import JsonMapSyntaxError
from jsonmap.data import Json


@dataclass
class JsonMapping:
    """Encapsulates the transformations to be performed on input JSON"""

    statements: List[ast.Statement]

    def __init__(self, program: str) -> None:
        try:
            program_tokens = tokens.tokenize(program)
            self.statements = ast.assemble(peekable(program_tokens))
        except JsonMapSyntaxError as syntax_error:
            traceback.print_exc()
            error.handle(syntax_error, program)
            raise syntax_error

    def apply(self, data: Json) -> Json:
        """Map a JSON document"""
        output: Dict[str | int, Json] = {}
        for statement in self.statements:
            if result := statement.evaluate(scope=data, universe=data):
                key, value = result
                output[key] = value
        return output
