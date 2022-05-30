"""
Run as a CLI
"""

from jsonmap.parse import parser

program = """
recipient := firstName;
last_name = "foo bar {}";
fizz := { buzz = "bang"; };
bar := for each foo.bar {
    whiz := bang;
    whoop = "dee do";
};
foo = "bar";
"""

parser.parse(program)
