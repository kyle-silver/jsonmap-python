# pylint: disable=missing-module-docstring,missing-class-docstring,missing-function-docstring

import json
from unittest import TestCase

from jsonmap import JsonMapping


class Mappings(TestCase):
    def test_reference_mapping(self) -> None:
        prog = JsonMapping("foo = &bar;")
        data = json.loads('{"foo": "hello, world!"}')
        actual = prog.apply(data)
        self.assertEqual(actual, {"bar": "hello, world!"})
