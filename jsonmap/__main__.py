"""
Run as a CLI
"""

# pylint: disable=invalid-name

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
lhs = [-1.765, {"foo": "bar"}];
"""

prog3 = """
"stringified left-hand side": &!first."name";
last_name: "foo bar {}";
fizz = { 
    buzz = { 
        whiz = "bang";
    }
    widget = &fuzz;
};
"json": {
    "fizz": {
        "buzz": "bang",
    },
    "foo": "bar"
},
"""

prog4 = """
list = map [{"foo": "bar"},{"foo": "fizz"}] {
    fizz = &buzz;
};
foo = "bar";
"fizz": &buzz;
"""

prog5 = """
list = zip &ref1 [&foo, &bar, {"fizz": "buzz"}] {
    foo = &bar;
}
"""

parser.parse(prog5)
