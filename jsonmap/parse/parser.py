"""
Parse program source code into something executable
"""

from jsonmap.parse import tokens


def parse(program: str) -> None:
    """Parse the program and (eventually) return something executable"""
    for token in tokens.tokenize(program):
        print(token)
