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
