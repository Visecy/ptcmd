"""Command decorators and classes for ptcmd.

This module provides the core functionality for creating and managing commands
with automatic argument parsing and completion.
"""

import sys
from argparse import ArgumentParser, Namespace, _SubParsersAction
from functools import partial, update_wrapper
from inspect import Parameter, signature
from types import MethodType
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    Generic,
    List,
    Literal,
    Optional,
    Sequence,
    Type,
    TypeVar,
    Union,
    cast,
    overload,
)

from typing_extensions import ParamSpec

from .argument import build_parser
from .completer import ArgparseCompleter
from .info import CommandInfo

if TYPE_CHECKING:
    from .core import BaseCmd


_P = ParamSpec("_P")
_P_Subcmd  = ParamSpec("_P_Subcmd")
_T = TypeVar("_T")
_T_Subcmd = TypeVar("_T_Subcmd")


class Command(Generic[_P, _T]):
    """Wrapper class that adds command metadata and argument parsing to a function.

    This class serves as the core command implementation in ptcmd, providing:
    - Automatic argument parsing from function signatures
    - Command metadata (name, hidden status, disabled status)
    - Argument completion support
    - Method binding for instance commands

    The Command class is typically created through the @command decorator rather
    than being instantiated directly.
    """

    def __init__(
        self,
        func: Callable[_P, _T],
        *,
        cmd_name: Optional[str] = None,
        parser: Optional[ArgumentParser] = None,
        unannotated_mode: Literal["strict", "autoconvert", "ignore"] = "autoconvert",
        parser_factory: Callable[..., ArgumentParser] = ArgumentParser,
        help_category: Optional[str] = None,
        hidden: bool = False,
        disabled: bool = False,
        _parent: Optional["Command"] = None,
    ) -> None:
        update_wrapper(self, func)
        self._parent = _parent
        self.__func__ = func
        if parser is None:
            parser = build_parser(
                MethodType(self.__func__, object()),
                unannotated_mode=unannotated_mode,
                parser_factory=parser_factory,
            )
        self.cmd_name = cmd_name
        self.parser = parser
        self.parser.set_defaults(__cmd_ins__=self)
        self.help_category = help_category
        self.hidden = hidden
        self.disabled = disabled

    @overload
    def add_subcommand(
        self,
        name: str,
        func: None = None,
        *,
        help: Optional[str] = None,
        aliases: Sequence[str] = (),
        add_help: bool = True,
        **kwds: Any,
    ) -> Callable[[Callable[_P_Subcmd, _T_Subcmd]], "Command[_P_Subcmd, _T_Subcmd]"]:
        ...

    @overload
    def add_subcommand(
        self,
        name: str,
        func: Callable[_P_Subcmd, _T_Subcmd],
        *,
        help: Optional[str] = None,
        aliases: Sequence[str] = (),
        add_help: bool = True,
        **kwds: Any,
    ) -> "Command[_P_Subcmd, _T_Subcmd]":
        ...

    def add_subcommand(
        self,
        name: str,
        func: Optional[Callable[_P_Subcmd, _T_Subcmd]] = None,
        *,
        help: Optional[str] = None,
        aliases: Sequence[str] = (),
        add_help: bool = True,
        **kwds: Any,
    ) -> Union[Callable[[Callable[_P_Subcmd, _T_Subcmd]], "Command[_P_Subcmd, _T_Subcmd]"], "Command[_P_Subcmd, _T_Subcmd]"]:
        subparser_action = self._ensure_subparsers()
        def inner(inner: Callable[_P_Subcmd, _T_Subcmd]) -> "Command[_P_Subcmd, _T_Subcmd]":
            return cast(Type[Command], self.__class__)(
                inner,
                cmd_name=name,
                parser_factory=partial(subparser_action.add_parser, name, help=help, aliases=aliases, add_help=add_help),
                parser=None,
                _parent=self,
                **kwds,
            )
        if func is None:
            return inner
        else:
            return inner(func)

    def invoke_from_argv(self, cmd: "BaseCmd", argv: List[str]) -> Any:
        """Invoke the command with parsed arguments.

        :param argv: List of argument strings to parse
        :type argv: List[str]
        :return: The result of the wrapped function
        :rtype: _T
        """
        parser: ArgumentParser = self.parser
        try:
            old_stdin = sys.stdin
            old_stdout = sys.stdout
            old_stderr = sys.stderr
            sys.stdin = cmd.stdin
            sys.stdout = sys.stderr = cmd.raw_stdout
            ns = parser.parse_args(argv)
        except SystemExit:
            return
        finally:
            sys.stdin = old_stdin
            sys.stdout = old_stdout
            sys.stderr = old_stderr
        return self.invoke_from_ns(cmd, ns)
    def invoke_from_ns(self, cmd: "BaseCmd", ns: Namespace) -> Any:
        cmd_ins = getattr(ns, "__cmd_ins__", self)
        cmd_chain = [cmd_ins]
        while cmd_ins._parent is not None and cmd_ins is not self:
            cmd_ins = cmd_ins._parent
            cmd_chain.append(cmd_ins)
        assert cmd_ins is self, f"Command chain is broken(root={cmd_ins})"

        ns.__cmd_chain__ = cmd_chain
        ret = None
        while cmd_chain:
            cmd_ins = cmd_chain.pop()
            ns.__cmd_result__ = ret
            ret = cmd_ins.invoke_inner(cmd, ns)
        return ret

    def invoke_inner(self, cmd: "BaseCmd", ns: Namespace) -> _T:
        func = MethodType(self.__func__, cmd)
        sig = signature(func)
        args, kwargs = [], {}
        for param_name, param in sig.parameters.items():
            if param.kind == Parameter.VAR_POSITIONAL:
                args.extend(getattr(ns, param_name, []))
            elif param.kind == Parameter.VAR_KEYWORD:
                kwargs.update(getattr(ns, param_name, {}))
            elif param.kind == Parameter.KEYWORD_ONLY:
                kwargs[param_name] = getattr(ns, param_name)
            else:
                args.append(getattr(ns, param_name))
        return func(*args, **kwargs)

    def _ensure_subparsers(self) -> _SubParsersAction:
        for action in self.parser._actions:
            if isinstance(action, _SubParsersAction):
                return action
        return self.parser.add_subparsers(metavar='SUBCOMMAND')

    @overload
    def __get__(self, instance: None, owner: Optional[type]) -> "Command[_P, _T]": ...

    @overload
    def __get__(self, instance: object, owner: Optional[type]) -> Callable[_P, _T]: ...

    def __get__(self, instance: Optional[object], owner: Optional[type]) -> Union["Command[_P, _T]", Callable[_P, _T]]:
        if instance is None:
            return self
        return self.__func__.__get__(instance, owner)

    def __cmd_info__(self, cmd: "BaseCmd") -> CommandInfo:
        if self.cmd_name:
            cmd_name = self.cmd_name
        else:
            assert self.__func__.__name__.startswith(cmd.COMMAND_FUNC_PREFIX), f"{self.__func__} is not a command function"
            cmd_name = self.__func__.__name__[len(cmd.COMMAND_FUNC_PREFIX) :]
        return CommandInfo(
            name=cmd_name,
            cmd_func=MethodType(self.invoke_from_argv, cmd),
            argparser=self.parser,
            completer=ArgparseCompleter(self.parser),
            category=self.help_category,
            hidden=self.hidden,
            disabled=self.disabled,
        )

    def __call__(self, *args: _P.args, **kwargs: _P.kwargs) -> _T:
        return self.__func__(*args, **kwargs)

    def __repr__(self) -> str:
        """Return detailed command representation."""
        parent_chain = []
        current = self._parent
        while current:
            parent_chain.append(current.cmd_name or "<root>")
            current = current._parent

        return (
            f"<Command(name={self.cmd_name!r}, "
            f"func={self.__func__.__name__}, "
            f"parent_chain={parent_chain[::-1]}, "
            f"parser={self.parser.prog if self.parser else None}, "
            f"hidden={self.hidden}, disabled={self.disabled}, "
            f"help_category={self.help_category!r})>"
        )


@overload
def auto_argument(
    func: Callable[_P, _T],
    *,
    parser: Optional[ArgumentParser] = None,
    unannotated_mode: Literal["strict", "autoconvert", "ignore"] = "autoconvert",
    parser_factory: Callable[..., ArgumentParser] = ArgumentParser,
    help_category: Optional[str] = None,
    hidden: bool = False,
    disabled: bool = False,
) -> Command[_P, _T]:
    """Decorator to convert a function into a command with automatic argument parsing.

    :param func: Function to decorate
    :type func: Callable[_P, _T]
    :param parser: Optional ArgumentParser to use (default: auto-generated)
    :type parser: Optional[ArgumentParser]
    :param unannotated_mode: Whether to allow unannotated arguments (default: autoconvert)
    :type unannotated_mode: Literal["strict", "autoconvert", "ignore"]
    :param parser_factory: Factory function for creating ArgumentParser instances
    :type parser_factory: Callable[..., ArgumentParser]
    :param help_category: Category for help/autocomplete
    :type help_category: Optional[str]
    :param hidden: Whether to hide the command from help/autocomplete
    :type hidden: bool
    :param disabled: Whether to disable the command
    :type disabled: bool
    :return: The decorated function
    :rtype: Command[_P, _T]
    """
    ...


@overload
def auto_argument(
    func: Optional[str] = None,
    *,
    parser: Optional[ArgumentParser] = None,
    unannotated_mode: Literal["strict", "autoconvert", "ignore"] = "autoconvert",
    parser_factory: Callable[..., ArgumentParser] = ArgumentParser,
    hidden: bool = False,
    disabled: bool = False,
) -> Callable[[Callable[_P, _T]], Command[_P, _T]]:
    """Decorator factory for auto_argument when called with parameters.

    :param func: None when used as a decorator factory
    :type func: None
    :param parser: Optional ArgumentParser to use (default: auto-generated)
    :type parser: Optional[ArgumentParser]
    :param unannotated_mode: Whether to allow unannotated arguments (default: autoconvert)
    :type unannotated_mode: Literal["strict", "autoconvert", "ignore"]
    :param parser_factory: Factory function for creating ArgumentParser instances
    :type parser_factory: Callable[..., ArgumentParser]
    :param help_category: Category for help/autocomplete
    :type help_category: Optional[str]
    :param hidden: Whether to hide the command from help/autocomplete
    :type hidden: bool
    :param disabled: Whether to disable the command
    :type disabled: bool
    :return: Decorator function
    :rtype: Callable[[Callable[_P, _T]], Command[_P, _T]]]
    """
    ...


def auto_argument(
    func: Union[Callable[_P, _T], str, None] = None,
    **kwds: Any
) -> Union[Command[_P, _T], Callable[[Callable[_P, _T]], Command[_P, _T]]]:
    name = func if isinstance(func, str) else None

    def inner(func: Callable[_P, _T]) -> Command[_P, _T]:
        return Command(
            func,
            cmd_name=name,
            **kwds,
        )

    if callable(func):
        return inner(func)
    else:
        return inner
