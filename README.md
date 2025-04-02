# ptcmd

[![License](https://img.shields.io/github/license/Visecy/ptcmd.svg)](LICENSE)
[![PyPI](https://img.shields.io/pypi/v/ptcmd.svg)](https://pypi.python.org/pypi/ptcmd)
[![Build Status](https://github.com/Visecy/ptcmd/actions/workflows/test_cov.yml/badge.svg)](https://github.com/Visecy/ptcmd/actions)
![PyPI - Downloads](https://img.shields.io/pypi/dw/ptcmd)
![Python Version](https://img.shields.io/badge/python-3.8%20|%203.9%20|%203.10%20|%203.11%20|%203.12-blue.svg)

A modern interactive command-line application building library based on `prompt_toolkit`

**Language: English/[中文](README_cn.md)**

## Features

- 🚀 Built on prompt_toolkit, providing powerful interactive experience
- 📝 Automatic argument parsing and completion
- 🌈 Rich text output support (using rich library)
- ⚡ Native async command support
- 🔍 Built-in command completion and shortcut key support

## Installation

Install from PyPI:

```bash
pip install ptcmd
```

Or install from source:

```bash
git clone https://github.com/Visecy/ptcmd.git
cd ptcmd
make install
```

## Quick Start

Create a simple command-line application:

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
In this simple example:

1. We created a class `MyApp` that inherits from `Cmd`
2. Defined a command method `do_hello` for the `hello` command
3. The command accepts an optional argument as a name
4. If no argument is provided, it defaults to "World"
5. We use the `self.poutput()` method to output the greeting
6. Finally, we start the interactive command-line interface with the `cmdloop()` method

This example demonstrates the most basic usage of ptcmd, including:
- Command definition method
- Argument processing
- Output display
- Program startup method

After running the program, enter the `hello` command to experience it:

```
(Cmd) hello
Hello, World!
(Cmd) hello Alice
Hello, Alice!
```

## Advanced Features

### Automatic Argument Parsing

```python
from ptcmd import Cmd, Arg, auto_argument

class MathApp(Cmd):
    @auto_argument
    def do_add(
        self, 
        x: float, 
        y: float,
        *,
        verbose: Arg[bool, "-v", "--verbose"] = False
    ):
        """Add two numbers
        :param x: First number
        :param y: Second number
        :param verbose: Show detailed output
        """
        result = x + y
        if verbose:
            self.poutput(f"{x} + {y} = {result}")
        else:
            self.poutput(result)
```

### Async Command Support

```python
import asyncio
from ptcmd import Cmd, auto_argument

class AsyncApp(Cmd):
    @auto_argument
    async def do_fetch(self, url: str):
        """Fetch URL content"""
        import aiohttp
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as resp:
                self.poutput(await resp.text())
```

## Library Comparison

Here's a comparison of the strengths and weaknesses of cmd, cmd2, and ptcmd libraries:

| Feature | cmd (standard lib) | cmd2 | ptcmd |
|------|-------------|------|-------|
| **Feature Richness** | Basic features | Most feature-rich | Relatively feature-rich |
| **Learning Curve** | Simple | Medium | Medium |
| **Interactive Experience** | Basic | Good | Excellent (based on prompt_toolkit) |
| **Auto-completion** | None | Supported | Supported |
| **Argument Parsing** | Manual handling | Requires building `ArgumentParser` | Automatic parsing |
| **Async Support** | None | None | Native support |
| **Rich Text Output** | None | Uses `cmd2.ansi` module | Uses `rich` library |
| **Dependencies** | None | Several | Most |
| **Performance** | High | Medium | Medium |
| **Use Cases** | Simple interactive CLI | Complex interactive CLI | Modern interactive CLI |

Main advantages:
- **cmd**: Python standard library, no extra dependencies, suitable for simple CLI applications
- **cmd2**: Comprehensive features, good community support, suitable for traditional CLIs requiring rich functionality
- **ptcmd**: Provides the best interactive experience, native async support, suitable for modern CLI applications

## Related Projects

- [prompt_toolkit](https://github.com/prompt-toolkit/python-prompt-toolkit): A Python library for building interactive command-line applications.
- [rich](https://github.com/Textualize/rich): A Python library for formatting text and output to the terminal.
- [typer](https://github.com/tiangolo/typer): A Python library for building command-line applications.
- [cmd2](https://github.com/python-cmd2/cmd2): A tool for building interactive command-line applications in Python. It aims to make it quick and easy for developers to build feature-rich and user-friendly interactive command-line applications.
- [argparse](https://docs.python.org/3/library/argparse.html): Python standard library for parsing command-line arguments and options.
- [cmd](https://github.com/python/cpython/blob/3.12/Lib/cmd.py): Python standard library for building interactive command-line applications.

## Special Thanks

- [cmd2](https://github.com/python-cmd2/cmd2): Provided inspiration for the project, and the command auto-completion logic also references this project.
- [Cline](https://cline.bot/): Helped quickly develop project prototypes and improve documentation and test cases.

## License

This project is licensed under the Apache License 2.0 - see the [LICENSE](LICENSE) file for details.

