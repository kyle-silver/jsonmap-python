"""
Parse program source code into something executable
"""

from more_itertools import peekable
from jsonmap.parse import tokens, ast


def parse(program: str) -> None:
    """Parse the program and (eventually) return something executable"""
    program_tokens = tokens.tokenize(program)
    for token in program_tokens:
        print(token)
    abstract_syntax_tree = ast.assemble(peekable(program_tokens))
    for node in abstract_syntax_tree:
        print(node)
