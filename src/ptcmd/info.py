"""Command information and metadata handling.

This module provides the CommandInfo class and related functionality for storing
and retrieving command metadata.
"""

from argparse import ArgumentParser
from types import MethodType
from typing import TYPE_CHECKING, Any, Callable, List, NamedTuple, Optional, Protocol, Union

from prompt_toolkit.completion import Completer

from . import constants
from .completer import ArgparseCompleter

if TYPE_CHECKING:
    from .core import BaseCmd


CMD_ATTR_ARGPARSER = "argparser"
CMD_ATTR_COMPLETER = "completer"
CMD_ATTR_HIDDEN = "hidden"
CMD_ATTR_DISABLED = "disabled"
CMD_ATTR_HELP_CATEGORY = "help_category"
CMD_ATTR_SHUTCUT = "shortcut"


class CommandInfo(NamedTuple):
    name: str
    cmd_func: Callable[[List[str]], Any]
    help_func: Optional[Callable[[bool], str]] = None
    category: Optional[str] = None
    completer: Optional[Completer] = None
    argparser: Optional[ArgumentParser] = None
    hidden: bool = False
    disabled: bool = False

    def __cmd_info__(self, cmd_ins: "BaseCmd", /) -> "CommandInfo":
        return self


class CommandInfoGetter(Protocol):
    def __cmd_info__(self, cmd_ins: "BaseCmd", /) -> CommandInfo:
        """Get the command information for this command.

        :param cmd_ins: The instance of the `cmd` class
        :type cmd_ins: "BaseCmd"
        :return: The command information
        """
        ...


def build_cmd_info(
    obj: Union[CommandInfoGetter, Callable[["BaseCmd", List[str]], Optional[bool]]], cmd: "BaseCmd"
) -> CommandInfo:
    if hasattr(obj, "__cmd_info__"):
        return obj.__cmd_info__(cmd)

    assert callable(obj), f"{obj} is not callable"
    assert obj.__name__.startswith(constants.COMMAND_FUNC_PREFIX), f"{obj} is not a command function"
    cmd_name = obj.__name__[len(constants.COMMAND_FUNC_PREFIX) :]
    if (constants.HELP_FUNC_PREFIX + cmd_name) in dir(cmd):
        help_func = getattr(cmd, constants.HELP_FUNC_PREFIX + cmd_name)
    else:
        help_func = None

    completer = getattr(obj, CMD_ATTR_COMPLETER, None)
    argparser = getattr(obj, CMD_ATTR_ARGPARSER, None)
    if completer is None and argparser is not None:
        completer = ArgparseCompleter(argparser)
    return CommandInfo(
        name=cmd_name,
        cmd_func=MethodType(obj, cmd),
        help_func=help_func,
        category=getattr(obj, CMD_ATTR_HELP_CATEGORY, None),
        completer=completer,
        argparser=argparser,
        hidden=getattr(obj, CMD_ATTR_HIDDEN, False),
        disabled=getattr(obj, CMD_ATTR_DISABLED, False),
    )
