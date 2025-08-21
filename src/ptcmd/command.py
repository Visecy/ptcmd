"""Command decorators and classes for ptcmd.

This module provides the core functionality for creating and managing commands
with automatic argument parsing and completion.
"""

from ast import literal_eval
from argparse import ArgumentParser, Namespace, _SubParsersAction
from functools import partial, update_wrapper
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

from rich_argparse import RichHelpFormatter
from typing_extensions import ParamSpec, Concatenate, Self

from .argument import build_parser, invoke_from_ns
from .completer import ArgparseCompleter
from .info import CommandInfo, CompleterGetterFunc, bind_parser

if TYPE_CHECKING:
    from .core import BaseCmd


_P = ParamSpec("_P")
_P_Method = ParamSpec("_P_Method")
_P_Subcmd = ParamSpec("_P_Subcmd")
_T = TypeVar("_T")
_T_Subcmd = TypeVar("_T_Subcmd")


class Command(Generic[_P, _T]):
    """Wrapper class that adds command metadata and argument parsing to a function.

    This class serves as the core command implementation in ptcmd, providing:
    - Automatic argument parsing from function signatures
    - Command metadata (name, hidden status, disabled status)
    - Argument completion support
    - Method binding for instance commands
    - Subcommand management

    The Command class is typically created through the @auto_argument decorator
    rather than being instantiated directly.
    """

    def __init__(
        self,
        func: Callable[_P, _T],
        *,
        cmd_name: Optional[str] = None,
        parser: Optional[ArgumentParser] = None,
        unannotated_mode: Literal["strict", "autoconvert", "ignore"] = "autoconvert",
        parser_factory: Optional[Callable[[], ArgumentParser]] = None,
        help_category: Optional[str] = None,
        hidden: bool = False,
        disabled: bool = False,
        _parent: Optional["Command"] = None,
    ) -> None:
        update_wrapper(self, func)
        self._parent = _parent
        self.__func__ = func
        if parser is None:
            if parser_factory is None:
                parser_factory = partial(
                    ArgumentParser, prog=func.__name__, description=func.__doc__, formatter_class=RichHelpFormatter
                )
            parser = build_parser(
                MethodType(self.__func__, object()),
                unannotated_mode=unannotated_mode,
                parser_factory=parser_factory,
            )
            if cmd_name is not None:
                parser.prog = cmd_name
        self.cmd_name = cmd_name
        self.parser = parser
        self.parser.set_defaults(__cmd_ins__=self)
        self.help_category = help_category
        self.hidden = hidden
        self.disabled = disabled
        self._completer_getter = None

    @overload
    def add_subcommand(
        self,
        name: str,
        func: None = None,
        *,
        help: Optional[str] = None,
        aliases: Sequence[str] = (),
        add_help: bool = True,
        unannotated_mode: Literal["strict", "autoconvert", "ignore"] = "autoconvert",
        help_category: Optional[str] = None,
        hidden: bool = False,
        disabled: bool = False,
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
        unannotated_mode: Literal["strict", "autoconvert", "ignore"] = "autoconvert",
        help_category: Optional[str] = None,
        hidden: bool = False,
        disabled: bool = False,
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
        """Add a subcommand to this command.

        This method can be used as a decorator or directly with a function.
        It creates a nested command structure where the current command acts as a parent.

        :param name: Name of the subcommand
        :type name: str
        :param func: The function to wrap as a subcommand (if provided directly)
        :type func: Optional[Callable[_P_Subcmd, _T_Subcmd]]
        :param help: Help text for the subcommand
        :type help: Optional[str]
        :param aliases: Aliases for the subcommand
        :type aliases: Sequence[str]
        :param add_help: Whether to add help for the subcommand
        :type add极_help: bool
        :param kwds: Additional keyword arguments for the Command constructor
        :type kwds: Any
        :return: Either a decorator function or a Command instance
        :rtype: Union[Callable[[Callable[_P_Subcmd, _T_Subcmd]], Command[_P_Subcmd, _T_Subcmd]], Command[_P_Subcmd, _T_Subcmd]]
        """
        subparser_action = self._ensure_subparsers()
        def inner(inner: Callable[_P_Subcmd, _T_Subcmd]) -> "Command[_P_Subcmd, _T_Subcmd]":
            if isinstance(func, Command):  # pragma: no cover
                raise TypeError("add_subcommand cannot be used with Command instances directly")
            return cast(Type[Command], self.__class__)(
                inner,
                cmd_name=None,
                parser_factory=partial(
                    subparser_action.add_parser,
                    name,
                    help=help,
                    aliases=aliases,
                    add_help=add_help,
                    description=inner.__doc__,
                    formatter_class=RichHelpFormatter,
                ),
                parser=None,
                _parent=self,
                **kwds,
            )
        if func is None:
            return inner
        else:
            return inner(func)

    def completer_getter(self, func: CompleterGetterFunc) -> CompleterGetterFunc:
        """Decorator to set a custom completer getter function for this command.

        The completer getter function should accept a BaseCmd instance and return a Completer.

        :param func: The completer getter function
        :type func: CompleterGetterFunc
        :return: The same function (for decorator chaining)
        :rtype: CompleterGetterFunc
        """
        self._completer_getter = func
        return func

    def invoke_from_argv(self, cmd: "BaseCmd", argv: List[str], *, parser: Optional[ArgumentParser] = None) -> Any:
        """Invoke the command with parsed arguments from a list of argv strings.

        This method parses command-line arguments and invokes the command function.
        It handles redirecting stdin/stdout during argument parsing.

        :param cmd: The BaseCmd instance this command belongs to
        :type cmd: "BaseCmd"
        :param argv: List of argument strings to parse
        :type argv: List[str]
        :param parser: Optional ArgumentParser to use (default: self.parser)
        :type parser: Optional[ArgumentParser]
        :return: The result of the wrapped function
        :rtype: Any
        """
        if parser is None:
            parser = self.parser
        argv = [
            literal_eval(arg)
            if (arg.startswith('"') and arg.endswith('"')) or (arg.startswith("'") and arg.endswith("'"))
            else arg
            for arg in argv
        ]
        try:
            ns = parser.parse_args(argv)
        except SystemExit:
            return
        return self.invoke_from_ns(cmd, ns)

    def invoke_from_ns(self, cmd: "BaseCmd", ns: Namespace) -> Any:
        """Invoke the command from a parsed namespace object.

        This method handles nested command invocation by traversing the command chain.

        :param cmd: The BaseCmd instance this command belongs to
        :type cmd: "BaseCmd"
        :param ns: The parsed argument namespace
        :type ns: Namespace
        :return: The result of the wrapped function
        :rtype: Any
        """
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
            ret = invoke_from_ns(MethodType(cmd_ins, cmd), ns)
        return ret

    def _ensure_subparsers(self) -> _SubParsersAction:
        """Ensure the command parser has a subparsers action.

        If the parser already has a subparsers action, return it.
        Otherwise, create a new one and return it.

        :return: The subparsers action for this command
        :rtype: _SubParsersAction
        """
        for action in self.parser._actions:
            if isinstance(action, _SubParsersAction):
                return action
        return self.parser.add_subparsers(metavar='SUBCOMMAND', required=True)

    @overload
    def __get__(self, instance: None, owner: Optional[type]) -> Self: ...

    @overload
    def __get__(
        self: "Command[Concatenate[Any, _P_Method], _T]", instance: object, owner: Optional[type]
    ) -> Callable[_P_Method, _T]: ...

    def __get__(self, instance: Optional[object], owner: Optional[type]) -> Callable[..., _T]:
        """Descriptor protocol implementation for method binding.

        This allows Command instances to behave like methods when accessed
        through a class instance.

        :param instance: The instance accessing the descriptor (None for class access)
        :type instance: Optional[object]
        :param owner: The class that owns the descriptor
        :type owner: Optional[type]
        :return: Either the Command instance or a bound method
        :rtype: Union["Command[_P, _T]", Callable[_P, _T]]
        """
        if instance is None:
            return self
        return self.__func__.__get__(instance, owner)

    def __cmd_info__(self, cmd: "BaseCmd") -> CommandInfo:
        """Get command information for this command.

        This method implements the CommandInfoGetter protocol, providing
        metadata about the command for use in help and completion.

        :param cmd: The BaseCmd instance this command belongs to
        :type cmd: "BaseCmd"
        :return: Command information object
        :rtype: CommandInfo
        """
        if self.cmd_name:
            cmd_name = self.cmd_name
        else:
            assert self.__func__.__name__.startswith(cmd.COMMAND_FUNC_PREFIX), f"{self.__func__} is not a command function"
            cmd_name = self.__func__.__name__[len(cmd.COMMAND_FUNC_PREFIX) :]
        parser = bind_parser(self.parser, cmd_name, cmd)
        if self._completer_getter is not None:
            completer = self._completer_getter(cmd)
        else:
            completer = ArgparseCompleter(parser)
        return CommandInfo(
            name=cmd_name,
            cmd_func=partial(self.invoke_from_argv, cmd, parser=parser),
            argparser=parser,
            completer=completer,
            category=self.help_category,
            hidden=self.hidden,
            disabled=self.disabled,
        )

    def __call__(self, *args: _P.args, **kwargs: _P.kwargs) -> _T:
        """Call the wrapped function directly.

        This allows Command instances to be used as callable objects.

        :param args: Positional arguments to pass to the wrapped function
        :type args: _P.args
        :param kwargs: Keyword arguments to pass to the wrapped function
        :type kwargs: _P.kwargs
        :return: The result of the wrapped function
        :rtype: _T
        """
        return self.__func__(*args, **kwargs)

    def __repr__(self) -> str:
        """Return detailed command representation.

        :return: String representation of the command
        :rtype: str
        """
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


@overload
def auto_argument(
    func: Optional[str] = None,
    *,
    parser: Optional[ArgumentParser] = None,
    unannotated_mode: Literal["strict", "autoconvert", "ignore"] = "autoconvert",
    parser_factory: Callable[..., ArgumentParser] = ArgumentParser,
    help_category: Optional[str] = None,
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


def auto_argument(
    func: Union[Callable[_P, _T], str, None] = None,
    **kwds: Any
) -> Union[Command[_P, _T], Callable[[Callable[_P, _T]], Command[_P, _T]]]:
    name = func if isinstance(func, str) else None

    def inner(func: Callable[_P, _T]) -> Command[_P, _T]:
        if isinstance(func, Command):  # pragma: no cover
            raise TypeError("auto_argument cannot be used with Command instances directly")
        return Command(
            func,
            cmd_name=name,
            **kwds,
        )

    if callable(func):
        return inner(func)
    else:
        return inner
