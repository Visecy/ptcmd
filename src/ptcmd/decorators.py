from argparse import ArgumentParser
from typing import Callable, Optional, TypeVar, Union, overload

from typing_extensions import ParamSpec

from . import command, constants


_T = TypeVar("_T")
_P = ParamSpec("_P")


@overload
def auto_argument(
        func: Callable[_P, _T],
        *,
        parser: Optional[ArgumentParser] = None,
        hidden: bool = False,
        disabled: bool = False
) -> Callable[_P, _T]:
    """Decorator to convert a function into a command with automatic argument parsing.

    :param func: Function to decorate
    :type func: Callable[_P, _T]
    :param parser: Optional ArgumentParser to use (default: auto-generated)
    :type parser: Optional[ArgumentParser]
    :param hidden: Whether to hide the command from help/autocomplete
    :type hidden: bool
    :param disabled: Whether to disable the command
    :type disabled: bool
    :return: The decorated function
    :rtype: Callable[_P, _T]
    """
    ...


@overload
def auto_argument(
        func: Optional[str] = None,
        *,
        parser: Optional[ArgumentParser] = None,
        hidden: bool = False,
        disabled: bool = False
) -> Callable[[Callable[_P, _T]], Callable[_P, _T]]:
    """Decorator factory for auto_argument when called with parameters.

    :param func: None when used as a decorator factory
    :type func: None
    :param parser: Optional ArgumentParser to use (default: auto-generated)
    :type parser: Optional[ArgumentParser]
    :param hidden: Whether to hide the command from help/autocomplete
    :type hidden: bool
    :param disabled: Whether to disable the command
    :type disabled: bool
    :return: Decorator function
    :rtype: Callable[[Callable[_P, _T]], Callable[_P, _T]]
    """
    ...


def auto_argument(
        func: Optional[Union[Callable[_P, _T], str]] = None,
        *,
        parser: Optional[ArgumentParser] = None,
        hidden: bool = False,
        disabled: bool = False
) -> Union[Callable[_P, _T], Callable[[Callable[_P, _T]], Callable[_P, _T]]]:
    """Implementation of the auto_argument decorator.

    Can be used both as a direct decorator (@auto_argument) or with parameters
    (@auto_argument(hidden=True)).

    :param func: Function to decorate or None when used with parameters
    :type func: Optional[Callable[_P, _T]]
    :param parser: Optional ArgumentParser to use (default: auto-generated)
    :type parser: Optional[ArgumentParser]
    :param hidden: Whether to hide the command from help/autocomplete
    :type hidden: bool
    :param disabled: Whether to disable the command
    :type disabled: bool
    :return: Either the decorated function or a decorator function
    :rtype: Union[Callable[_P, _T], Callable[[Callable[_P, _T]], Callable[_P, _T]]]
    """
    name = func if isinstance(func, str) else None
    def wrapper(func: Callable[_P, _T]) -> Callable[_P, _T]:
        if name is not None:
            _name = name
        else:
            assert func.__name__.startswith(constants.COMMAND_FUNC_PREFIX), f"{func} is not a command function"
            _name = func.__name__[len(constants.COMMAND_FUNC_PREFIX):]
        return command.Command(_name, func, parser=parser, hidden=hidden, disabled=disabled)
    if callable(func):
        return wrapper(func)
    else:
        return wrapper
