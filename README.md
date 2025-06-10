# ptcmd

[![License](https://img.shields.io/github/license/Visecy/ptcmd.svg)](LICENSE)
[![PyPI](https://img.shields.io/pypi/v/ptcmd.svg)](https://pypi.python.org/pypi/ptcmd)
[![Build Status](https://github.com/Visecy/ptcmd/actions/workflows/test_cov.yml/badge.svg)](https://github.com/Visecy/ptcmd/actions)
![PyPI - Downloads](https://img.shields.io/pypi/dw/ptcmd)
![Python Version](https://img.shields.io/badge/python-3.8%20|%203.9%20|%203.10%20|%203.11%20|%203.12-blue.svg)

A modern interactive command-line application building library based on `prompt_toolkit`

**Language: English/[中文](README_cn.md)**

## 1. Features

- 🚀 Built on `prompt_toolkit` for powerful interactive experiences
- 📝 Automatic parameter parsing and completion  
- 🌈 Rich text output support (using `rich` library)
- ⚡ Native async command support
- 🔍 Built-in command completion and shortcut keys

## 2. Installation

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

## 3. Quick Start

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

In this basic example:

1. We create a `MyApp` class inheriting from `Cmd`
2. Define a `do_hello` command method
3. The command accepts an optional name parameter
4. Uses "World" if no parameter is provided
5. Output greeting using `self.poutput()`
6. Start the CLI with `cmdloop()`

This example demonstrates:
- Command definition syntax
- Parameter handling
- Output display
- Application startup process

Run the program and try the `hello` command:

```
(Cmd) hello
Hello, World!
(Cmd) hello Alice
Hello, Alice!
```

## 4. Advanced Features

### 4.1 Auto Argument Parsing

For complex commands, use the `auto_argument` decorator with type hints for automatic argument parsing:

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
    ) -> None:
        """Add two numbers"""
        result = x + y
        if verbose:
            self.poutput(f"{x} + {y} = {result}")
        else:
            self.poutput(result)
```

This approach automatically generates equivalent argparse code:
- Converts positional parameters to required arguments
- Converts keyword parameters to optional flags
- Handles type conversion and validation

### 4.2 Rich Text Output

Leverage rich library for styled output:

```python
class RichApp(Cmd):
    def do_hello(self, argv: list[str]) -> None:
        self.poutput(f"[bold blue]Hello, World![/bold blue]")
```

For advanced formatting, access the console directly:

```python
class RichApp(Cmd):
    def do_hello(self, argv: list[str]) -> None:
        with self.console.pager(styles=True):
            self.console.print("Hello, World!", style="bold blue")
```

### 4.3 Subcommand Support

For command functions that use the automatic parameter parsing feature, `ptcmd` allows you to add any number of sub-commands to them in a simple way. The execution order of command functions is starting from the root command and then executing them one by one.

1. Single-level subcommand example:

```python
from ptcmd import Cmd, auto_argument

class App(Cmd):
    @auto_argument
    def do_math(self):
        """Math operations"""
        
    @do_math.add_subcommand("add")
    def add(self, x: float, y: float):
        """Addition"""
        self.poutput(f"{x} + {y} = {x + y}")
```

Usage examples:
```
(Cmd) math add 5 3
5.0 + 3.0 = 8.0
(Cmd) math sub 5 3
5.0 - 3.0 = 2.0
```

2. Multi-level subcommand example:

```python
from ptcmd import Cmd, auto_argument

class App(Cmd):
    @auto_argument
    def do_server(self):
        """Server management"""
        
    @do_server.add_subcommand("db")
    def db(self):
        """Database management"""
        
    @db.add_subcommand("migrate")
    def migrate(self, version: str):
        """Execute database migration"""
        self.poutput(f"Migrating to version {version}...")

    @do_server.add_subcommand("cache")
    def cache(self):
        """Cache management"""
        
    @cache.add_subcommand("clear")
    def clear(self, confirm: bool = False):
        """Clear cache"""
        if confirm:
            self.poutput("Cache cleared")
        else:
            self.poutput("Please add --confirm to proceed")
```

Usage examples:
```
(Cmd) server db migrate v1.2.0
Migrating to version v1.2.0...
(Cmd) server cache clear --confirm  
Cache cleared
```

### 4.4 Async Command Support

Native async/await support for I/O bound operations:

```python
import aiohttp
from ptcmd import Cmd, auto_argument

class AsyncApp(Cmd):
    @auto_argument
    async def do_get(self, url: str):
        """Fetch URL content"""
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as resp:
                self.poutput(await resp.text(), markup=False)
```

## 5. Library Comparison

| Feature              | cmd (stdlib) | cmd2            | ptcmd                   |
|----------------------|--------------|-----------------|-------------------------|
| **Rich Output**      | No           | Basic           | Rich library support    |
| **Auto Completion**  | No           | Yes             | Yes                     |
| **Argument Parsing** | Manual       | argparse        | Automatic               |
| **Async Support**    | No           | No              | Native                  |
| **Dependencies**     | None         | Several         | Most                    |
| **Learning Curve**   | Simple       | Moderate        | Moderate                |
| **Use Case**         | Simple CLI   | Traditional CLI | Modern Interactive CLI  |

Key Advantages:
- **cmd**: Standard library, no dependencies
- **cmd2**: Feature-rich traditional CLI
- **ptcmd**: Modern interactive experience with best-in-class UX

## 6. Related Projects

- [prompt_toolkit](https://github.com/prompt-toolkit/python-prompt-toolkit) - Foundation for building powerful interactive command lines
- [rich](https://github.com/Textualize/rich) - Enables rich text formatting and beautiful output
- [typer](https://github.com/tiangolo/typer) - Modern CLI framework with type hints
- [cmd2](https://github.com/python-cmd2/cmd2) - Inspiration for many ptcmd features
- [argparse](https://docs.python.org/3/library/argparse.html) - Python's standard argument parsing library
- [cmd](https://docs.python.org/3/library/cmd.html) - Python's standard line-oriented command interpreters library

## 7. Special Thanks

- [cmd2](https://github.com/python-cmd2/cmd2) for inspiring the command completion system
- [Cline](https://cline.bot/) for assisting with project documentation and test cases

## 8 License

Apache License 2.0 - See [LICENSE](LICENSE)
