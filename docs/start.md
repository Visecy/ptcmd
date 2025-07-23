# Getting Started

## Installation

Install from PyPI (recommended):

```bash
pip install ptcmd
```

Or install from source:

```bash
git clone https://github.com/Visecy/ptcmd.git
cd ptcmd
make install
```

To run unit tests, use:

```bash
make develop test
```

To build documentation locally, use:
```bash
make develop docs
```

## Basic Application Structure

ptcmd applications generally follow a consistent pattern: inherit from the `Cmd` class, define command methods using the `do_` prefix convention, then create an instance and call the `cmdloop()` method to start the interaction.

## Creating Your First Application

Let's start with the simplest application:

```python
import sys
from ptcmd import Cmd

class MyApp(Cmd):
    def do_hello(self, argv: list[str]) -> None:
        """Hello World!"""
        if argv:
            name = argv[0]
        else:
            name = "World"
        self.poutput(f"Hello, {name}!")

if __name__ == "__main__":
    sys.exit(MyApp().cmdloop())
```

We defined a class named `MyApp` that inherits from `Cmd`, with a single command `hello`. Now we can run this script:

```
(Cmd) hello
Hello, World!
(Cmd) hello Alice
Hello, Alice!
(Cmd) exit
```

When we enter the `hello` command, we get the desired output. Don't forget to enter the `exit` command to quit the program.

## Using Declarative Argument Parsing

The previous example has a minor issue: it ignores additional arguments. This isn't good practice. We could add conditionals or use `argparse` to handle this, but these approaches aren't concise and produce boilerplate code.

`ptcmd` provides a declarative argument parsing approach that automatically analyzes function signatures to perform argument parsing. This uses the `@auto_argument` decorator:

```python
import sys
from ptcmd import Cmd, auto_argument

class MyApp(Cmd):
    @auto_argument
    def do_hello(self, name: str = "World") -> None:
        """Hello World!"""
        self.poutput(f"Hello, {name}!")

if __name__ == "__main__":
    sys.exit(MyApp().cmdloop())
```

Now we've implemented a more robust command with cleaner code. You can use the `-h/--help` parameter to get command information:

```
(Cmd) hello
Hello, World!
(Cmd) hello Alice
Hello, Alice!
(Cmd) hello -h
Usage: hello [-h] [name]

Hello World!

Positional Arguments:
  name

Optional Arguments:
  -h, --help  show this help message and exit
```

## Next Steps

- View the [User Guide](./user_guide/index.md) for more detailed instructions.
- Explore [Examples](./examples/index.md) for additional sample applications.
- Refer to the [API Reference](./api/index.md) for detailed API definitions.
