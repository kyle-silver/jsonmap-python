"""
Parse program source code into something executable
"""

from jsonmap import tokens

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


tokenized = tokens.tokenize(program)

for token in tokenized:
    print(token)
