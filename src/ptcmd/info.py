"""Command information and metadata handling.

This module provides the CommandInfo class and related functionality for storing
and retrieving command metadata.
"""

import copy
from argparse import Action, ArgumentParser, _SubParsersAction
from contextlib import suppress
from types import MethodType
from typing import TYPE_CHECKING, Any, Callable, Coroutine, List, NamedTuple, Optional, Protocol, TypeVar, Union

from prompt_toolkit.completion import Completer
from rich.text import Text

from .completer import ArgparseCompleter

if TYPE_CHECKING:
    from .core import BaseCmd


CommandFunc = Callable[[Any, List[str]], Union[Optional[bool], Coroutine[None, None, Optional[bool]]]]
CommandLike = Union["CommandInfoGetter", CommandFunc]
HelpGetterFunc = Callable[[bool], str]
ArgparserGetterFunc = Callable[[Any], ArgumentParser]
CompleterGetterFunc = Callable[[Any], Completer]

T_CommandFunc = TypeVar(
    "T_CommandFunc",
    Callable[[Any, List[str]], bool],
    Callable[[Any, List[str]], None],
    Callable[[Any, List[str]], Coroutine[None, None, bool]],
    Callable[[Any, List[str]], Coroutine[None, None, None]],
)

CMD_ATTR_NAME = "cmd_name"
CMD_ATTR_ARGPARSER = "argparser"
CMD_ATTR_COMPLETER = "completer"
CMD_ATTR_HIDDEN = "hidden"
CMD_ATTR_DISABLED = "disabled"
CMD_ATTR_HELP_CATEGORY = "help_category"
CMD_ATTR_SHUTCUT = "shortcut"
PARSER_ATTR_CMD = "cmd_ins"
PARSER_ATTR_NAME = "cmd_name"
ACTION_ATTR_CMD = "cmd_ins"
ACTION_ATTR_NAME = "cmd_name"


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
) -> Callable[[T_CommandFunc], T_CommandFunc]:
    def inner(func: T_CommandFunc) -> T_CommandFunc:
        if name is not None:
            setattr(func, CMD_ATTR_NAME, name)
        setattr(func, CMD_ATTR_ARGPARSER, argparser)
        setattr(func, CMD_ATTR_COMPLETER, completer)
        setattr(func, CMD_ATTR_HELP_CATEGORY, help_category)
        setattr(func, CMD_ATTR_HIDDEN, hidden)
        setattr(func, CMD_ATTR_DISABLED, disabled)
        return func

    return inner


def bind_parser(parser: ArgumentParser, cmd_name: str, cmd_ins: "BaseCmd") -> ArgumentParser:
    """
    Binds an ArgumentParser to a command function.

    Creates a copy of the parser, sets its prog to the full command path,
    and binds the command name and command instance to the parser and all
    its actions. Handles subparsers recursively. Raises ValueError if
    the parser is already bound.

    :param parser: The ArgumentParser to bind
    :type parser: ArgumentParser
    :param cmd_name: The name of the command
    :type cmd_name: str
    :param cmd_ins: The instance of the command
    :type cmd_ins: BaseCmd
    :return: The bound ArgumentParser
    :rtype: ArgumentParser
    :raises ValueError: If parser is already bound
    """
    # Check if parser is already bound
    if hasattr(parser, PARSER_ATTR_CMD):  # pragma: no cover
        raise ValueError("parser is already bound to a command")

    # Create a shallow copy of the parser
    new_parser = copy.copy(parser)

    # Build full command path for this parser
    if ' ' in new_parser.prog:
        cmds = new_parser.prog.split(' ')
        cmds[0] = cmd_name
        new_parser.prog = ' '.join(cmds)
    else:
        new_parser.prog = cmd_name

    # Bind command metadata to parser
    with suppress(AttributeError):
        setattr(new_parser, PARSER_ATTR_CMD, cmd_ins)
        setattr(new_parser, PARSER_ATTR_NAME, cmd_name)

    # Set _print_message to use cmd_ins.poutput
    with suppress(AttributeError):
        new_parser._print_message = lambda message, file = None: cmd_ins.poutput(Text(message))

    # Process all actions in the parser
    new_actions = []
    for action in new_parser._actions:
        action = copy.copy(action)
        # Bind command metadata to action
        with suppress(AttributeError):
            setattr(action, ACTION_ATTR_CMD, cmd_ins)
            setattr(action, ACTION_ATTR_NAME, cmd_name)

        # Handle subparsers recursively
        if isinstance(action, _SubParsersAction):
            for n, subparser in action.choices.items():
                # Recursively bind subparsers
                action.choices[n] = bind_parser(subparser, cmd_name, cmd_ins)
        new_actions.append(action)

    new_parser._actions = new_actions
    return new_parser


def get_cmd_ins(obj: Union["BaseCmd", ArgumentParser, Action]) -> Optional["BaseCmd"]:
    """Get the BaseCmd instance from an object.

    :param obj: The object to get the BaseCmd instance from
    :type obj: Union[BaseCmd, ArgumentParser, Action]
    :return: The BaseCmd instance
    :rtype: Optional[BaseCmd]
    """
    from .core import BaseCmd
    if isinstance(obj, BaseCmd):  # pragma: no cover
        return obj
    elif isinstance(obj, ArgumentParser):
        return getattr(obj, PARSER_ATTR_CMD, None)
    elif isinstance(obj, Action):
        return getattr(obj, ACTION_ATTR_CMD, None)
