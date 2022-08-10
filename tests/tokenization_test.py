# pylint: disable=missing-module-docstring,missing-class-docstring,missing-function-docstring

from pprint import pprint
from unittest import TestCase

from jsonmap import tokens
from jsonmap.tokens import BareWord, ListIndexReferenceToken, LiteralToken, ReferenceToken, Symbol, SymbolToken


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

    def test_list_index_reference(self) -> None:
        actual = tokens.tokenize("foo = map [] {bar = &?;}")
        self.assertTrue(ListIndexReferenceToken(position=21, path=[], global_scope=False) in actual)

    def test_zipped_list_references(self) -> None:
        actual = tokens.tokenize(
            """
            foo = zip &fizz &buzz {
                bar = &?.1;
                baz = &?.-10;
            }
            """
        )
        pprint(actual)
        self.assertTrue(ListIndexReferenceToken(position=60, path=[1], global_scope=False) in actual)
        self.assertTrue(ListIndexReferenceToken(position=88, path=[-10], global_scope=False) in actual)
