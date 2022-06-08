"""
Parse program source code into something executable
"""
import pprint
import traceback

from more_itertools import peekable
from jsonmap.parse import tokens, ast, error
from jsonmap.parse.error import JsonMapSyntaxError


def parse(program: str) -> None:
    """Parse the program and (eventually) return something executable"""
    try:
        program_tokens = tokens.tokenize(program)
        abstract_syntax_tree = ast.assemble(peekable(program_tokens))
        pprint.pprint(abstract_syntax_tree)
    except JsonMapSyntaxError as syntax_error:
        traceback.print_exc()
        error.handle(syntax_error, program)
