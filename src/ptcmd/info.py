"""Command information and metadata handling.

This module provides the CommandInfo class and related functionality for storing
and retrieving command metadata.
"""

from argparse import ArgumentParser
from types import MethodType
from typing import TYPE_CHECKING, Any, Callable, List, NamedTuple, Optional, Protocol, Union

from prompt_toolkit.completion import Completer

from .completer import ArgparseCompleter

if TYPE_CHECKING:
    from .core import BaseCmd


CommandFunc = Callable[[Any, List[str]], Optional[bool]]
CommandLike = Union["CommandInfoGetter", CommandFunc]
HelpGetterFunc = Callable[[bool], str]
ArgparserGetterFunc = Callable[[Any], ArgumentParser]
CompleterGetterFunc = Callable[[Any], Completer]

CMD_ATTR_NAME = "cmd_name"
CMD_ATTR_ARGPARSER = "argparser"
CMD_ATTR_COMPLETER = "completer"
CMD_ATTR_HIDDEN = "hidden"
CMD_ATTR_DISABLED = "disabled"
CMD_ATTR_HELP_CATEGORY = "help_category"
CMD_ATTR_SHUTCUT = "shortcut"


class CommandInfo(NamedTuple):
    name: str
    cmd_func: Callable[[List[str]], Any]
    help_func: Optional[HelpGetterFunc] = None
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


def build_cmd_info(obj: CommandLike, cmd: "BaseCmd") -> CommandInfo:
    if hasattr(obj, "__cmd_info__"):
        return obj.__cmd_info__(cmd)

    assert callable(obj), f"{obj} is not callable"
    if getattr(obj, CMD_ATTR_NAME, None) is not None:
        cmd_name = getattr(obj, CMD_ATTR_NAME)
    else:
        assert obj.__name__.startswith(cmd.COMMAND_FUNC_PREFIX), f"{obj} is not a command function"
        cmd_name = obj.__name__[len(cmd.COMMAND_FUNC_PREFIX) :]
    if (cmd.HELP_FUNC_PREFIX + cmd_name) in dir(cmd):
        help_func = getattr(cmd, cmd.HELP_FUNC_PREFIX + cmd_name)
    else:
        help_func = None

    completer: Any = getattr(obj, CMD_ATTR_COMPLETER, None)
    argparser: Any = getattr(obj, CMD_ATTR_ARGPARSER, None)
    if callable(argparser):
        argparser = argparser(cmd)
    if completer is None and argparser is not None:
        completer = ArgparseCompleter(argparser)
    elif callable(completer):
        completer = completer(cmd)
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


def set_info(
    name: Optional[str] = None,
    *,
    argparser: Optional[Union[ArgparserGetterFunc, ArgumentParser]] = None,
    completer: Optional[Union[CompleterGetterFunc, Completer]] = None,
    help_category: Optional[str] = None,
    hidden: bool = False,
    disabled: bool = False,
) -> Callable[[CommandFunc], CommandFunc]:
    def inner(func: CommandFunc) -> CommandFunc:
        if name is not None:
            setattr(func, CMD_ATTR_NAME, name)
        setattr(func, CMD_ATTR_ARGPARSER, argparser)
        setattr(func, CMD_ATTR_COMPLETER, completer)
        setattr(func, CMD_ATTR_HELP_CATEGORY, help_category)
        setattr(func, CMD_ATTR_HIDDEN, hidden)
        setattr(func, CMD_ATTR_DISABLED, disabled)
        return func

    return inner
