"""A modern command-line interface framework built on prompt_toolkit.

ptcmd provides a declarative way to build rich, interactive CLI applications with:

Key Features:
- Automatic argument parsing with type annotations
- Intelligent tab completion
- Syntax highlighting and rich text formatting
- Asynchronous command execution
- Customizable command structure and organization
- Built-in help system generation

Basic Usage:
```python
import sys
from ptcmd import Cmd, Arg, auto_argument

class MyApp(Cmd):
    @auto_argument
    def do_hello(
        self,
        name: Arg[str, {"help": "Your name"}] = "World",  # noqa: F821,B002
        times: Arg[int, "--times"] = 1  # noqa: F821,B002
    ) -> None:
        for _ in range(times):
            self.poutput(f"Hello {name}!")

if __name__ == "__main__":
    sys.exit(MyApp().cmdloop())
```

:copyright: (c) 2025 by the Visecy.
:license: Apache 2.0, see LICENSE for more details.
"""

from .argument import Arg, Argument
from .command import Command, auto_argument
from .info import set_info
from .core import BaseCmd, Cmd
from .version import __version__

__all__ = [
    "Arg",
    "Argument",
    "Command",
    "BaseCmd",
    "Cmd",
    "auto_argument",
    "set_info",
]
