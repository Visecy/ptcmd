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
```python linenums="1"
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

Copyright 2025 Visecy

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""

from .argument import Arg, Argument
from .command import Command, auto_argument
from .info import set_info
from .core import BaseCmd, Cmd
from .version import __version__  # noqa: F401

__all__ = [
    "Arg",
    "Argument",
    "Command",
    "BaseCmd",
    "Cmd",
    "auto_argument",
    "set_info",
]
