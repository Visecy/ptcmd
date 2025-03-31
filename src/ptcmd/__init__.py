"""ptcmd package.

A modern cmd library based on prompt_toolkit.
"""

from .version import __version__
from .argument import Arg, Argument
from .command import Command
from .core import BaseCmd, Cmd
from .decorators import auto_argument


__all__ = [
    "Arg",
    "Argument",
    "Command",
    "BaseCmd",
    "Cmd",
    "auto_argument",
    "__version__",
]
