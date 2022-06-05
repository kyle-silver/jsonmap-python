# pylint: disable=missing-module-docstring,missing-class-docstring,missing-function-docstring

from unittest import TestCase

from jsonmap.parse import tokens
from jsonmap.parse.tokens import BareWord, ReferenceToken, Symbol, SymbolToken


class SingleStatementTokenization(TestCase):
    def test_simple_assignment(self) -> None:
        actual = tokens.tokenize("lhs = &rhs;")
        self.assertEqual(actual[0], BareWord(0, "lhs"))
        self.assertEqual(actual[1], SymbolToken(4, Symbol.assignment))
        self.assertEqual(actual[2], ReferenceToken(7, path=["rhs"]))
        self.assertEqual(actual[3], SymbolToken(10, Symbol.end_of_statement))
