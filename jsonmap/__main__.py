"""
Run as a CLI
"""

from jsonmap.parse import parser, tokens

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
lhs = [1, 2, 3];
"""

prog3 = """
"stringified left-hand side": &!first."name";
last_name: "foo bar {}";
fizz = { 
    buzz = { 
        whiz = "bang";
    }
    widget = &wocket;
}
"json": {
    "foo": "bar",
    "fizz": {
        "buzz": "bang",
    }
}
"""

parser.parse(prog3)

# print(tokens.tokenize("lhs = &rhs;"))
