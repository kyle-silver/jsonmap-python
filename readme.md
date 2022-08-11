# A Friendly Mini-Language for Mapping JSON

`jsonmap` is a small, domain-specific language for transforming JSON documents. It&rsquo;s intended for expressing simple transformations clearly. Let&rsquo;s jump into some examples.

- [Tutorial](#tutorial)
  - [References](#references)
  - [Objects](#objects)
  - [List Aggregation](#list-aggregation)
  - [Map](#map)
  - [Zip](#zip)
  - [Bind](#bind)
  - [Outside Data in Bound Scopes](#outside-data-in-bound-scopes)

## Tutorial

Say that we want to transform this JSON object:

```jsonc
// this is what we start with
{
    "actor": "Alice",
    "line": "Hello, world!"
}

// this is what we want to get: just some simple field renaming
{
    "speaker": "Alice",
    "message": "Hello, world!"
}
```

This program would get the job done:

```txt
speaker = &actor;
message = &line
```

On the left-hand side of each statement, we say what we want the name of the field to be in the output object. On the right-hand side we **reference** the name of the field in the input object with the data we want using the `&` symbol.

### References

We can use the reference operator to reach into nested objects as well. This input, for example

```jsonc
{
    "actor": {
        "first_name": "Alice",
        "last_name": "Smith"
    },
    "line": "Hello, world!"
}
```

can be mapped with the following program:

```txt
speaker = &actor.first_name;
message = &line;
```

You can use quotes with a reference if you key includes whitespace:

```jsonc
{
    "actor": {
        "first name": "Alice",
        "last name": "Smith"
    },
    "line": "Hello, world!"
}
```

For example:

```txt
speaker = &actor."first name";
message = &line;
```

If you need to select a specific element from an array, you can use a numeric index to pull that item out.

```jsonc
// input
{
    "fruits": ["apples", "bananas", "cherries"]
}

// output
{
    "my_favorite_fruit": "bananas"
}
```

We use the dot `.` to index into lists, not square brackets.

```txt
my_favorite_fruit = &fruits.1;
```

### Objects

We can re-structure our JSON output to whatever shape we would like. For example, say we need to perform the following transformation:

```jsonc
// input
{
    "fifth_grade_teacher": "Bob",
    "fifth_grade_students": 25
}

// output
{
    "classroom": {
        "teacher": "Bob",
        "number_of_students": 25,
        "grade_level": 5
    }
}
```

This will require us to create a new JSON object instead of having our output be flat. To create a nested object in the output of a function, simply enclose it in a pair of curly braces.

```txt
classroom = {
    "teacher": &fifth_grade_teacher,
    "number_of_students": &fifth_grade_students,
    "grade_level": 5
}
```

In this example uses colons and commas instead of equals signs and semicolons for a program that looks closer to native JSON. It is equivalent, though to this program:

```txt
classroom = {
    teacher = &fifth_grade_teacher;
    number_of_students = &fifth_grade_students;
    grade_level = 5;
}
```

You can also see from this example that we can insert JSON literals anywhere into our program. The 5 was not in our input data, but we were able to hard-code it.

### List Aggregation

Sometimes, you need to turn a flat grouping of field values into a list. Just like we can create our own objects, we can also create our own lists in the output.

```jsonc
// input
{
    "fruit_1": {
        "type": "apples",
        "quantity": 30,
    },
    "fruit_2": {
        "type": "bananas",
        "quantity": 17,
    },
    "fruit_3": {
        "type": "cherries",
        "quantity": 90
    }
}

// output
{
    "fruits": ["apples", "bananas", "cherries"]
}
```

In this case, we can insert a list-literal.

```txt
fruits = [&fruit_1.type, &fruit_2.type, &fruit_3.type];
```

### Map

Often rather than create a list from scratch, we need to transform an existing list. In those cases, we can use the `map` function to apply a set of transformations to each item in a list.

```jsonc
// input
{
    "schedule": [
        {
            "class": "medieval literature",
            "time": "10:00"
        },
        {
            "class": "algorithms",
            "time": "13:00"
        },
        {
            "class": "underwater basket weaving",
            "time": "15:00"
        }
    ]
}

// output
{
    "classes": ["medieval literature", "algorithms", "underwater basket weaving"]
}
```

This program will populate the list with the `class` field of each item.

```txt
classes = map &schedule [
    &class
]
```

If we instead wanted our output list to be populated with objects, we can use curly braces instead of square braces and put in statements similar to how we did for our one-off object mapping.

```jsonc
// output
{
    "classes": [
        { "subject": "medieval literature" },
        { "subject": "algorithms" },
        { "subject": "underwater basket weaving"},
    ]
}
```

This program should do the trick nicely.

```txt
classes = map &schedule {
    subject = &class;
}
```

Maps can also be over lists of non-objects. This is a silly but succinct example.

```jsonc
// input
{
    "values": [1, 2, 3]
}

// output
{
    "favorite_numbers": [
        { "value": 1 },
        { "value": 2 },
        { "value": 3 },
    ]
}
```

This program uses an extension of the reference operator, the **anonymous reference** written as `&?`, to reference the entire object stored in the list rather than a field within that object.

```txt
favorite_numbers = map &values {
    value = &?;
}
```

### Zip

The `zip` operation is useful when you need to iterate pairwise over multiple lists. It can take any number of lists as an input.

```jsonc
// input
{
    "names": [
        { "name": "alice" }, 
        { "name": "bob" }
    ],
    "grades": [
        { "grade": "a" }, 
        { "grade": "b" }
    ]
}

// output
{
    "grades": [
        {
            "name": "alice", 
            "grade": "a"
        },
        {
            "name": "bob", 
            "grade": "b"
        },
    ]
}
```

Commas are not needed to separate arguments to `zip`

```txt
grades = zip &names &grades {
    name = &name;
    grade = &grade;
}
```

If instead we need to reference a list of non-objects, we can use an extension of the anonymous reference, the **indexed anonymous reference**, to indicate from which positional argument we would like to pull the value. It is zero-indexed.

This program

```txt
numbers = zip [1, 2, 3] ["one", "two", "three"] {
    value: &?.0,
    name: &?.1,
}
```

will yield the following output:

```json
{
    "numbers": [
        { "value": 1, "name": "one" },
        { "value": 2, "name": "two" },
        { "value": 3, "name": "three" },
    ]
}
```

When zipping, all of the namespaces from the arguments are merged.

### Bind

In cases where we need to pull a lot of data out of an object, writing the name over and over again can get tiring.

```txt
details = {
    first_name = &customer_profile.identifiers.first_name;
    middle_name = &customer_profile.identifiers.middle_name;
    last_name = &customer_profile.identifiers.middle_name;
}
```

The `bind` keyword can help cut down on this kind of clutter.

```txt
details = bind &customer_profile.identifiers {
    first_name = &first_name;
    middle_name = &middle_name;
    last_name = &last_name;
}
```

When you use `map` or `zip`, the namespaces are automatically bound.

### Outside Data in Bound Scopes

Sometimes when operating in a bound namespace, you will want to reference data outside of the namespace. The **global reference**, written as `&!`, will give you access to that global namespace.

```jsonc
// input
{
    "store": "Alice's Fruit Stand",
    "inventory": [
        "apples",
        "bananas",
        "cherries"
    ]
}

// output
{
    "items": [
        {
            "item": "apples",
            "store": "Alice's Fruit Stand"
        }, 
        {
            "item": "bananas",
            "store": "Alice's Fruit Stand"
        },
        {
            "item": "cherries",
            "store": "Alice's Fruit Stand"
        }
    ]
```

The global reference always starts from the very top namespace of the object.

```txt
items = map &inventory {
    item = &?;
    store = &!store;
}
```
