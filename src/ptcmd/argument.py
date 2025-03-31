import warnings
from argparse import Action
from argparse import ArgumentParser
from argparse import FileType
from inspect import Parameter, Signature, signature
from typing import (TYPE_CHECKING, Any, Callable, Iterable, Literal, Mapping,
                    Optional, Tuple, Type, TypeVar, Union)

from typing_extensions import (Annotated, Self, get_args, get_origin,
                               get_type_hints)


class Argument:
    """
    Represents a command-line argument to be added to an ArgumentParser.

    This class allows defining argparse arguments in a declarative way, either directly
    or through type annotations using `Annotated` (aliased as `Arg` for convenience).

    :param args: Positional arguments for the argument.
    :param kwargs: Keyword arguments for the argument.

    Usage:

    ```py
    version: Arg[
        str,
        "-v", "--version",
        {"action": "version", "version": "0.1.0"}
    ]

    # Or using Annotated
    version: Annotated[
        str,
        Argument(
            "-v", "--version",
            action="version",
            version="0.1.0"
        )
    ]
    ```
    """

    __slots__ = ["args", "kwargs", "dest"]

    if TYPE_CHECKING:

        def __init__(
            self,
            *name_or_flags: str,
            action: Union[str, Type[Action]] = ...,
            nargs: Union[int, str, None] = None,
            const: Any = ...,
            default: Any = ...,
            type: Union[Callable[[str], Any], FileType, str] = ...,
            choices: Iterable[Any] = ...,
            required: bool = ...,
            help: Optional[str] = ...,
            metavar: Union[str, Tuple[str, ...], None] = ...,
            dest: Optional[str] = ...,
            version: str = ...,
            **kwargs: Any,
        ) -> None: ...
    else:

        def __init__(self, *args, **kwds) -> None:
            self.args = args
            self.kwargs = kwds

    def set_name(self, /, name: str, *, keyword: bool = False) -> None:
        """
        Sets the name of the argument.

        :param name: The name to set for the argument.
        :type name: str
        """
        if not self.args:
            self.args = (f"--{name}",) if keyword else (name,)
        if not keyword:
            return
        if "dest" in self.kwargs and self.kwargs["dest"] != name:  # pragma: no cover
            warnings.warn("dest is overwritten")
        self.kwargs["dest"] = name

    def set_default(self, /, default: Any, *, keyword: bool = False) -> None:
        """
        Sets the default value of the argument.

        :param default: The default value to set for the argument.
        :type default: Any
        """
        if "default" in self.kwargs and self.kwargs["default"] != default:  # pragma: no cover
            warnings.warn("default value is overwritten")
        self.kwargs["default"] = default
        if not keyword:
            self.kwargs["nargs"] = "?"

    def set_nargs(self, /, nargs: Union[int, str, None]) -> None:
        """
        Sets the number of arguments for the argument.

        :param nargs: The number of arguments for the argument.
        :type nargs: Union[int, str, None]
        """
        if "nargs" in self.kwargs and self.kwargs["nargs"] != nargs:  # pragma: no cover
            warnings.warn("nargs is overwritten")
        self.kwargs["nargs"] = nargs

    def __class_getitem__(cls, args: Any) -> Annotated:
        """Create an Annotated type with Argument metadata for type annotations.

        This enables the Argument class to be used in type annotations to define
        command-line arguments in a declarative way.

        :param args: Either:
            - A single type (e.g. `Argument[str]`)
            - A tuple of (type, *names, Argument) (e.g. `Argument[str, "-f", "--file"]`)
            - A tuple of (type, *names, dict) (e.g. `Argument[str, "-f", {"help": "file"}]`)
        :type args: Any
        :return: An Annotated type containing the argument specification
        :rtype: Annotated
        :raises TypeError: If argument names are not strings
        """
        if not isinstance(args, tuple):
            tp = args
            args = ()
        else:
            tp, *args = args

        if args and isinstance(args[-1], cls):
            arg_ins: Self
            *args, arg_ins = args
            arg_ins.args = tuple(args) + arg_ins.args
            return Annotated[tp, arg_ins]
        elif args and isinstance(args[-1], Mapping):
            *args, kwargs = args
            if "type" not in kwargs and "action" not in kwargs and callable(tp):
                kwargs["type"] = tp
        elif tp is bool:
            kwargs = {"action": "store_true"}
        elif callable(tp):
            kwargs = {"type": tp}

        if not all(isinstance(arg, str) for arg in args):
            raise TypeError("argument name must be str")
        return Annotated[tp, cls(*args, **kwargs)]  # type: ignore

    def __call__(self, parser: ArgumentParser) -> ArgumentParser:
        """
        Adds the argument to the provided ArgumentParser.

        :param parser: The ArgumentParser to add the argument to.
        :type parser: ArgumentParser
        :return: The ArgumentParser with the argument added.
        :rtype: ArgumentParser
        """
        parser.add_argument(*self.args, **self.kwargs)
        return parser

    def __eq__(self, value: Any) -> bool:
        if not isinstance(value, Argument):
            return False
        return self.args == value.args and self.kwargs == value.kwargs

    __hash__ = object.__hash__

    def __repr__(self) -> str:
        """
        Returns a string representation of the Argument instance.

        :return: A string representation of the Argument instance.
        :rtype: str
        """
        return f"{self.__class__.__qualname__}({self.args}, {self.kwargs})"


if TYPE_CHECKING:
    Arg = Annotated
    """Type alias for Annotated when used in type checking mode."""
else:
    Arg = Argument
    """Type alias for Argument that enables declarative argument definitions.

    Example:
    ```py
    def cmd(
        file: Arg[str, "-f", "--file", {"help": "Input file"}],
        verbose: Arg[bool, "-v", "--verbose"]
    ) -> None: ...
    ```
    """


def get_argument(annotation: Any) -> Optional[Argument]:
    """
    Retrieves the Argument instance from an annotation.

    :param annotation: The annotation to retrieve the Argument instance from.
    :type annotation: Any
    :return: The Argument instance if found, otherwise None.
    :rtype: Optional[Argument]
    """
    if isinstance(annotation, Argument):
        return annotation
    if get_origin(annotation) is not Annotated:
        return

    _, *metadata = get_args(annotation)
    for arg in metadata:
        if isinstance(arg, Argument):
            return arg


_T_Parser = TypeVar("_T_Parser", bound=ArgumentParser)


def build_parser(
    func: Union[Callable, Signature],
    *,
    unannotated_mode: Literal["strict", "autoconvert", "ignore"] = "strict",
    parser_factory: Callable[..., _T_Parser] = ArgumentParser,
) -> _T_Parser:
    """Build an ArgumentParser from a function's type-annotated signature.

    :param func: The function or signature to build parser from
    :type func: Union[Callable, Signature]
    :param unannotated_mode: How to handle parameters without Argument metadata:
        - "strict": Raise TypeError
        - "autoconvert": Infer Argument from type annotation
        - "ignore": Skip unannotated parameters
    :type unannotated_mode: Literal["strict", "autoconvert", "ignore"]
    :param parser_factory: Factory function to create the parser
    :type parser_factory: Callable[..., _T_Parser]
    :return: Configured ArgumentParser instance
    :rtype: _T_Parser
    :raises TypeError: For unsupported parameter kinds or strict mode violations
    :raises ValueError: For invalid unannotated_mode values

    Example:
    ```py
    def example(
        path: Arg[str, "--path", {"help": "Input path"}],
        force: Arg[bool, "--force", {"action": "store_true"}],
        *,
        timeout: int = 10,
    ) -> None: ...

    parser = build_parser(example, unannotated_mode="autoconvert")
    ```
    """
    if isinstance(func, Signature):  # pragma: no cover
        sig = func
        parser = parser_factory()
        type_hints = {}
    else:
        parser = parser_factory(prog=func.__name__, description=func.__doc__)
        sig = signature(func)
        type_hints = get_type_hints(func, include_extras=True)

    for param_name, param in sig.parameters.items():
        annotation = type_hints.get(param_name, param.annotation)
        if param.kind == Parameter.VAR_KEYWORD:
            raise TypeError("var keyword arguments are not supported")
        argument = get_argument(annotation)
        if argument is None:
            if unannotated_mode == "strict":
                raise TypeError(f"{param_name} is not annotated with Argument")
            elif unannotated_mode == "autoconvert":
                argument = get_argument(Arg[annotation]) if annotation is not Parameter.empty else Argument()
                if argument is None:
                    raise TypeError(f"{param_name} is not annotated with Argument and cannot be inferred from type")
            elif unannotated_mode == "ignore":
                continue
            else:
                raise ValueError(f"unsupported unannotated_mode: {unannotated_mode}")

        argument.set_name(param_name, keyword=param.kind == Parameter.KEYWORD_ONLY)
        if param.kind == Parameter.VAR_POSITIONAL:
            argument.set_nargs("*")
        elif param.default is not Parameter.empty:
            argument.set_default(param.default, keyword=param.kind == Parameter.KEYWORD_ONLY)

        argument(parser)

    return parser
