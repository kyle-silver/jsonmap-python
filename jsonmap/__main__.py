"""
Run as a CLI
"""

# pylint: disable=invalid-name

from pprint import pprint
from jsonmap.parser import JsonMapping

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

pprint(actual)
