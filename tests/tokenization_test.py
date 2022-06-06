# pylint: disable=missing-module-docstring,missing-class-docstring,missing-function-docstring

from unittest import TestCase

from jsonmap.parse import tokens
from jsonmap.parse.tokens import BareWord, LiteralToken, ReferenceToken, Symbol, SymbolToken


class SingleStatementTokenization(TestCase):
    def test_simple_assignment(self) -> None:
        actual = tokens.tokenize("lhs = &rhs;")
        self.assertEqual(actual[0], BareWord(0, "lhs"))
        self.assertEqual(actual[1], SymbolToken(4, Symbol.assignment))
        self.assertEqual(actual[2], ReferenceToken(7, path=["rhs"]))
        self.assertEqual(actual[3], SymbolToken(10, Symbol.end_of_statement))

    def test_colon_assignment(self) -> None:
        actual = tokens.tokenize("lhs: &rhs;")
        self.assertEqual(actual[0], BareWord(0, "lhs"))
        self.assertEqual(actual[1], SymbolToken(3, Symbol.assignment))
        self.assertEqual(actual[2], ReferenceToken(6, path=["rhs"]))
        self.assertEqual(actual[3], SymbolToken(9, Symbol.end_of_statement))

    def test_string_literals(self) -> None:
        actual = tokens.tokenize('"lhs" = "rhs",')
        self.assertEqual(actual[0], LiteralToken(0, "lhs"))
        self.assertEqual(actual[1], SymbolToken(6, Symbol.assignment))
        self.assertEqual(actual[2], LiteralToken(8, "rhs"))
        self.assertEqual(actual[3], SymbolToken(13, Symbol.end_of_statement))

    def test_list_assignment(self) -> None:
        actual = iter(tokens.tokenize('lhs = [1,2,3, 4,"6",7];'))
        self.assertEqual(next(actual), BareWord(0, "lhs"))
        self.assertEqual(next(actual), SymbolToken(4, Symbol.assignment))
        self.assertEqual(next(actual), SymbolToken(6, Symbol.left_square_bracket))
        self.assertEqual(next(actual), BareWord(7, "1"))
        self.assertEqual(next(actual), SymbolToken(8, Symbol.end_of_statement))
        self.assertEqual(next(actual), BareWord(9, "2"))
        self.assertEqual(next(actual), SymbolToken(10, Symbol.end_of_statement))
        self.assertEqual(next(actual), BareWord(11, "3"))
        self.assertEqual(next(actual), SymbolToken(12, Symbol.end_of_statement))
        self.assertEqual(next(actual), BareWord(14, "4"))
        self.assertEqual(next(actual), SymbolToken(15, Symbol.end_of_statement))
        self.assertEqual(next(actual), LiteralToken(16, "6"))
        self.assertEqual(next(actual), SymbolToken(19, Symbol.end_of_statement))
        self.assertEqual(next(actual), BareWord(20, "7"))
        self.assertEqual(next(actual), SymbolToken(21, Symbol.right_square_bracket))
        self.assertEqual(next(actual), SymbolToken(22, Symbol.end_of_statement))
