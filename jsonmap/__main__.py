"""
Run as a CLI
"""

from jsonmap.parse import parser

prog1 = """
recipient = &firstName;
last_name = "foo bar {}";
fizz = { buzz = "bang"; };
bar = map &foo.bar {
    whiz = &bang;
    whoop = "dee do";
    globally_mapped = &!firstName."middle name".lastName;
};
foo = "bar";
computed_value = `${interpolated} ${text}`;
"""

prog2 = """
"stringified left-hand side" = &!first."name";
last_name = "foo bar {}";
"""

parser.parse(prog2)
