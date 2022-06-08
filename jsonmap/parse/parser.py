"""
Parse program source code into something executable
"""
from __future__ import annotations

from dataclasses import dataclass
import pprint
import traceback
from typing import List

from more_itertools import peekable
from jsonmap.parse import tokens, ast, error
from jsonmap.parse.error import JsonMapSyntaxError


@dataclass(frozen=True)
class Program:
    statements: List[ast.Statement]

    @staticmethod
    def parse(program: str) -> Program:
        try:
            program_tokens = tokens.tokenize(program)
            abstract_syntax_tree = ast.assemble(peekable(program_tokens))
            return Program(abstract_syntax_tree)
        except JsonMapSyntaxError as syntax_error:
            traceback.print_exc()
            error.handle(syntax_error, program)
            raise syntax_error


def parse(program: str) -> None:
    """Parse the program and (eventually) return something executable"""
    try:
        program_tokens = tokens.tokenize(program)
        abstract_syntax_tree = ast.assemble(peekable(program_tokens))
        pprint.pprint(abstract_syntax_tree)
    except JsonMapSyntaxError as syntax_error:
        traceback.print_exc()
        error.handle(syntax_error, program)
        raise syntax_error
