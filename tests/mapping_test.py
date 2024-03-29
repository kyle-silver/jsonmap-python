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

    def test_nested_bind(self) -> None:
        actual = JsonMapping(
            """
            foo = bind &"first scope" {
                bar = bind &"second scope" {
                    fizz = &buzz;
                }
            }
            """
        ).apply({"first scope": {"second scope": {"buzz": "hello"}}})
        self.assertEqual(
            actual,
            {
                "foo": {
                    "bar": {
                        "fizz": "hello",
                    }
                }
            },
        )

    def test_map(self) -> None:
        actual = JsonMapping(
            """
            student_first_names = map &students {
                name = &first_name;
            }
            """
        ).apply({"students": [{"first_name": "alice"}, {"first_name": "bob"}]})
        self.assertEqual(actual, {"student_first_names": [{"name": "alice"}, {"name": "bob"}]})

    def test_map_on_array_literals(self) -> None:
        actual = JsonMapping(
            """
            names = map [{"first_name": &"first_student"}, {"first_name": "bob"}] {
                "name": &"first_name"
            }
            """
        ).apply({"first_student": "alice"})
        self.assertEqual(actual, {"names": [{"name": "alice"}, {"name": "bob"}]})

    def test_anonymous_values(self) -> None:
        actual = JsonMapping(
            """
            names = map &students [&first_name];
            """
        ).apply({"students": [{"first_name": "alice"}, {"first_name": "bob"}]})
        self.assertEqual(actual, {"names": ["alice", "bob"]})

    def test_silly_but_legal_anonymous_mapping(self) -> None:
        actual = JsonMapping(
            """
            names = map &students [{"first name": &"first_name", "last name": &"last_name"}]
            """
        ).apply(
            {
                "students": [
                    {"first_name": "alice", "last_name": "aardvark"},
                    {"first_name": "bob", "last_name": "badger"},
                ]
            }
        )
        self.assertEqual(
            actual,
            {
                "names": [
                    {"first name": "alice", "last name": "aardvark"},
                    {"first name": "bob", "last name": "badger"},
                ]
            },
        )

    def test_simple_zip(self) -> None:
        actual = JsonMapping(
            """
            grades = zip &names &grades {
                name = &name;
                grade = &grade;
            }
            """
        ).apply(
            {
                "names": [{"name": "alice"}, {"name": "bob"}],
                "grades": [{"grade": "a"}, {"grade": "b"}],
            }
        )
        self.assertEqual(
            actual,
            {
                "grades": [
                    {"name": "alice", "grade": "a"},
                    {"name": "bob", "grade": "b"},
                ]
            },
        )

    def test_zip_array(self) -> None:
        actual = JsonMapping(
            """
            numbers = zip [{"value": 1}, {"value": 2}] &names {
                value: &value,
                name: &name,
            }
            """
        ).apply(
            {
                "names": [{"name": "one"}, {"name": "two"}],
            }
        )
        self.assertEqual(
            actual,
            {
                "numbers": [
                    {"value": 1, "name": "one"},
                    {"value": 2, "name": "two"},
                ]
            },
        )

    def test_list_indexed_map(self) -> None:
        actual = JsonMapping(
            """
            numbers = map &values {
                name = &?;
            }
            """
        ).apply({"values": [1, 2, 3]})

        self.assertEqual(
            actual,
            {
                "numbers": [
                    {"name": 1},
                    {"name": 2},
                    {"name": 3},
                ]
            },
        )

    def test_list_indexed_zip(self) -> None:
        actual = JsonMapping(
            """
            numbers = zip [1,2,3] ["one", "two", "three"] {
                "value": &?.0,
                "name": &?.1,
            }
            """
        ).apply({})
        self.assertEqual(
            actual,
            {
                "numbers": [
                    {"value": 1, "name": "one"},
                    {"value": 2, "name": "two"},
                    {"value": 3, "name": "three"},
                ]
            },
        )
