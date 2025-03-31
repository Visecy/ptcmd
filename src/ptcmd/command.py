"""Command decorators and classes for ptcmd.

This module provides the core functionality for creating and managing commands
with automatic argument parsing and completion.
"""

from argparse import ArgumentParser
from inspect import Parameter, signature
import sys
from types import MethodType
from typing import TYPE_CHECKING, Callable, Generic, List, Literal, Optional, TypeVar, Union, overload
from matplotlib.pylab import f
from typing_extensions import ParamSpec

from .info import CommandInfo
from .argument import build_parser
from .completer import ArgparseCompleter

if TYPE_CHECKING:
    from .core import BaseCmd


_P = ParamSpec("_P")
_T = TypeVar("_T")


class Command(Generic[_P, _T]):
    """Wrapper class that adds command metadata and argument parsing to a function.
    """
    def __init__(
        self,
        name: str,
        func: Callable[_P, _T],
        *,
        parser: Optional[ArgumentParser] = None,
        unannotated_mode: Literal["strict", "autoconvert", "ignore"] = "autoconvert",
        parser_factory: Callable[..., ArgumentParser] = ArgumentParser,
        hidden: bool = False,
        disabled: bool = False,
    ) -> None:
        self.__name__ = name
        self.__func__ = func
        if parser is None:
            parser = build_parser(
                MethodType(self.__func__, object()),
                unannotated_mode=unannotated_mode,
                parser_factory=parser_factory,
            )
        self.parser = parser
        self.completer = ArgparseCompleter(parser)
        self.hidden = hidden
        self.disabled = disabled

    def invoke(self, cmd: "BaseCmd", argv: List[str]) -> Optional[_T]:
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
        func = MethodType(self.__func__, cmd)
        sig = signature(func)
        args, kwargs = [], {}
        for param_name, param in sig.parameters.items():
            if param.kind == Parameter.VAR_POSITIONAL:
                args.extend(getattr(ns, param_name, []))
            elif param.kind == Parameter.VAR_KEYWORD:
                kwargs.update(getattr(ns, param_name, {}))
            elif param.kind == Parameter.POSITIONAL_ONLY:
                args.append(getattr(ns, param_name))
            else:
                kwargs[param_name] = getattr(ns, param_name)
        return func(*args, **kwargs)  # type: ignore
    
    @overload
    def __get__(self, instance: None, owner: Optional[type]) -> "Command[_P, _T]": ...
    
    @overload
    def __get__(self, instance: object, owner: Optional[type]) -> Callable[_P, _T]: ...

    def __get__(self, instance: Optional[object], owner: Optional[type]) -> Union["Command[_P, _T]", Callable[_P, _T]]:
        if instance is None:
            return self
        return self.__func__.__get__(instance, owner)
    
    def __cmd_info__(self, cmd: "BaseCmd") -> CommandInfo:
        return CommandInfo(
            name=self.__name__,
            cmd_func=MethodType(self.invoke, cmd),
            argparser=self.parser,
            completer=self.completer,
            hidden=self.hidden,
            disabled=self.disabled,
        )

    def __call__(self, *args: _P.args, **kwargs: _P.kwargs) -> _T:
        return self.__func__(*args, **kwargs)

    @property
    def __wrapped__(self) -> Callable[_P, _T]:
        return self.__func__
