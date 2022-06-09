# pylint: disable=missing-module-docstring,missing-class-docstring,missing-function-docstring

import json
from unittest import TestCase

from jsonmap import JsonMapping


class Mappings(TestCase):
    def test_reference_mapping(self) -> None:
        mapping = JsonMapping("foo = &bar;")
        data = json.loads('{"bar": "hello, world!"}')
        actual = mapping.apply(data)
        self.assertEqual(actual, {"foo": "hello, world!"})

    def test_reference_and_literal_mappings(self) -> None:
        mapping = JsonMapping(
            """
            foo = &bar;
            fizz = "buzz";
            count = 5;
            """
        )
        data = json.loads('{"bar": "hello, world!"}')
        actual = mapping.apply(data)
        self.assertEqual(
            actual,
            {
                "foo": "hello, world!",
                "fizz": "buzz",
                "count": 5,
            },
        )

    def test_array_indexing(self) -> None:
        mapping = JsonMapping("foo = &bar.0; fizz = &bar.1;")
        data = json.loads('{"bar": ["hello", "world"]}')
        actual = mapping.apply(data)
        self.assertEqual(actual, {"foo": "hello", "fizz": "world"})

    def test_null_values(self) -> None:
        mapping = JsonMapping('foo: null, "fizz": &"bar",')
        data = json.loads('{"bar": null}')
        actual = mapping.apply(data)
        self.assertEqual(actual, {"foo": None, "fizz": None})

    def test_deep_reference(self) -> None:
        mapping = JsonMapping("foo = &bar.fizz.buzz;")
        data = json.loads('{"bar": {"fizz": {"buzz": 0}}}')
        actual = mapping.apply(data)
        self.assertEqual(actual, {"foo": 0})

    def test_scope(self) -> None:
        mapping = JsonMapping(
            """
            foo = {
                bar = &fizz,
                "buzz": {"baz": &boo}
            },
            """
        )
        data = json.loads('{"fizz": ["hello"], "boo": "world"}')
        actual = mapping.apply(data)
        self.assertEqual(
            actual,
            {
                "foo": {
                    "bar": ["hello"],
                    "buzz": {"baz": "world"},
                }
            },
        )

    def test_array_evaluation(self) -> None:
        actual = JsonMapping(
            """
            foo = [null, 1.4, "hello", &bar, [0, 1, 2], {whiz = &bang}];
            """
        ).apply(json.loads('{"bar": "hello", "bang": "world"}'))
        self.assertEqual(
            actual,
            {
                "foo": [None, 1.4, "hello", "hello", [0, 1, 2], {"whiz": "world"}],
            },
        )

    def test_bind(self) -> None:
        actual = JsonMapping(
            """
            foo = bind &bar {
                "first": &first,
                "second": &second.third,
                fourth: &!fourth
            }
            """
        ).apply(
            {
                "fourth": 4,
                "bar": {
                    "first": 1,
                    "second": {"third": 3},
                },
            }
        )
        self.assertEqual(actual, {"foo": {"first": 1, "second": 3, "fourth": 4}})
