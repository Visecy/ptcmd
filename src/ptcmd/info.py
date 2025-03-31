from argparse import ArgumentParser
from types import MethodType
from typing import TYPE_CHECKING, Any, Callable, List, NamedTuple, Optional, Protocol, Union

from prompt_toolkit.completion import Completer

from . import constants

if TYPE_CHECKING:
    from .core import BaseCmd


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


def build_cmd_info(obj: Union[CommandInfoGetter, Callable[["BaseCmd", List[str]], Optional[bool]]], cmd: "BaseCmd") -> CommandInfo:
    if hasattr(obj, "__cmd_info__"):
        return obj.__cmd_info__(cmd)
    
    assert callable(obj), f"{obj} is not callable"
    assert obj.__name__.startswith(constants.COMMAND_FUNC_PREFIX), f"{obj} is not a command function"
    cmd_name = obj.__name__[len(constants.COMMAND_FUNC_PREFIX):]
    if (constants.HELP_FUNC_PREFIX + cmd_name) in dir(cmd):
        help_func = getattr(cmd, constants.HELP_FUNC_PREFIX + cmd_name)
    else:
        help_func = None
    return CommandInfo(
        name=cmd_name,
        cmd_func=MethodType(obj, cmd),
        help_func=help_func,
        category=getattr(obj, constants.CMD_ATTR_HELP_CATEGORY, None),
        completer=getattr(obj, constants.CMD_ATTR_COMPLETER, None),
        argparser=getattr(obj, constants.CMD_ATTR_ARGPARSER, None),
        hidden=getattr(obj, constants.CMD_ATTR_HIDDEN, False),
        disabled=getattr(obj, constants.CMD_ATTR_DISABLED, False),
    )
