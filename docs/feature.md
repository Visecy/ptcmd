# Features

This document provides a comprehensive overview of the core features and characteristics of `ptcmd`. It explains how the framework combines modern Python libraries to create a powerful CLI development experience. For implementation details of core framework classes, refer to the Core Framework. For detailed usage patterns and examples, see Examples and Usage.

## Powerful Interactive Experience

`ptcmd` is built on the modern interactive library `prompt_toolkit`, offering a modern command-line experience that goes beyond basic text input/output. The framework automatically handles complex terminal interactions, providing completion and syntax highlighting.

![syntax_highlighting](/ptcmd/assets/syntax-highlighting.png)

## Declarative Argument Parsing

`ptcmd` eliminates boilerplate argument parsing code through the `@auto_argument` decorator and `Arg` type hints. The system automatically generates `ArgumentParser` instances based on function signatures, making command definitions both concise and type-safe.

```python linenums="1"
from ptcmd import Cmd, Arg, auto_argument

class MathApp(Cmd):
    @auto_argument
    def do_add(
        self, 
        x: float, 
        y: float,
        *,
        verbose: Arg[bool, "-v", "--verbose", {"help": "Verbose output"}] = False
    ) -> None:
        """Add two numbers"""
        result = x + y
        if verbose:
            self.poutput(f"{x} + {y} = {result}")
        else:
            self.poutput(result)
```

The above example is equivalent to:

```python linenums="1"
from ptcmd import Cmd, Arg, auto_argument
from argparse import ArgumentParser

class MathApp(Cmd):
    def do_add(self, argv: list[str]) -> None:
        parser = ArgumentParser(prog="add", description="Add two numbers")
        parser.add_argument("x", type=float)
        parser.add_argument("y", type=float)
        parser.add_argument("-v", "--verbose", action="store_true")
        ns = parser.parse_args(argv)
        result = ns.x + ns.y
        if ns.verbose:
            self.poutput(f"{ns.x} + {ns.y} = {result}")
        else:
            self.poutput(result)
```

If you're using a type checker, using `Arg` may be flagged as an error. You can add `# noqa: F821,F722,B002` at the end of the line to have the type checker ignore these issues. If this concerns you, you can use `Annotated` with `Argument` for a more compliant declaration, though this is more verbose and loses some automatic inference features.

```python linenums="1"
from typing import Annotated
from ptcmd import Cmd, Argument, auto_argument

class MathApp(Cmd):
    @auto_argument
    def do_add(
        self, 
        x: float, 
        y: float,
        *,
        verbose: Annotated[bool, Argument("-v", "--verbose", action="store_true")] = False
    ) -> None:
        """Add two numbers"""
        result = x + y
        if verbose:
            self.poutput(f"{x} + {y} = {result}")
        else:
            self.poutput(result)
```

## Rich Text Output

`ptcmd` integrates the `rich` library to provide advanced text formatting, styling, and layout capabilities. The framework encapsulates `rich.Console` functionality while maintaining compatibility with existing print-based code.

The `Cmd` class exposes a `console` property, which is a `rich.Console` object for printing rich text. You can also use the wrapped methods `poutput`, `pwarning`, `perror`, etc., which indirectly print rich text through the `console`.

```python linenums="1"
class RichApp(Cmd):
    def do_hello(self, argv: list[str]) -> None:
        # Output using rich markup
        self.poutput(f"[bold blue]Hello, World![/bold blue]")
```

The prompt supports rich text styling using either `rich` or `prompt_toolkit`.

```python linenums="1"
class RichTextApp(Cmd):
    DEFAULT_PROMPT = "[cmd.prompt]rich[/cmd.prompt]> "

    @auto_argument
    def do_test_card(self) -> None:
        """Show rich text"""
        self.poutput(make_test_card())
```

![test_card](/ptcmd/assets/test_card.png)

## Automatic Command Completion

`ptcmd` can automatically understand command structures, argument types, and available values based on the `ArgumentParser` instance information provided by commands. This enables automatic command completion through `prompt_toolkit`'s `Completer`.

Completion defaults to the `READLINE_LIKE` style, which resembles terminal completion.

![auto_complete](/ptcmd/assets/completion.png)

You can also use the `MULTI_COLUMN` completion style provided by `prompt_toolkit`.

![multi_column_completion](/ptcmd/assets/multi_column_completion.png)

## Arbitrary Multi-level Subcommands

`ptcmd` supports adding arbitrary levels of subcommands to a command.

```python linenums="1"
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
            self.poutput("Please add --confirm to confirm the operation")
```

## Native Asynchronous Support

Thanks to `prompt_toolkit`'s excellent asynchronous support, `ptcmd` natively supports asynchronous commands.

```python linenums="1"
from typing import Any, Optional
from aiohttp import ClientSession
from ptcmd import Cmd, auto_argument


class RequestApp(Cmd):
    DEFAULT_PROMPT = "[cmd.prompt]request[/cmd.prompt]> "

    @auto_argument
    async def do_get(self, url: str, *, params: Optional[str] = None) -> None:
        """Send a GET request to the specified URL"""
        async with ClientSession() as session:
            async with session.get(url, params=params) as response:
                content = await response.text()
                self.poutput(f"Response from {url}:\n{content}")

    @auto_argument
    async def do_post(self, url: str, data: Any) -> None:
        """Send a POST request to the specified URL with data"""
        async with ClientSession() as session:
            async with session.post(url, data=data) as response:
                content = await response.text()
                self.poutput(f"Response from {url}:\n{content}")


if __name__ == "__main__":
    RequestApp().cmdloop()
```
