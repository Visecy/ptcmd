import warnings
from argparse import Action, ArgumentParser, FileType
from inspect import Parameter, Signature, signature
from typing import TYPE_CHECKING, Any, Callable, Iterable, Literal, Mapping, Optional, Tuple, Type, TypeVar, Union

from typing_extensions import Annotated, Self, get_args, get_origin, get_type_hints


class Argument:
    """Represents a command-line argument to be added to an ArgumentParser.

    This class provides a declarative way to define argparse arguments, either directly
    or through type annotations using `Annotated` (aliased as `Arg` for convenience).

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

        def __init__(self, *args: str, **kwds: Any) -> None:
            """Initialize an Argument instance with names/flags and keyword arguments.

            :param args: Positional arguments (names/flags) for the argument
            :type args: str
            :param kwds: Keyword arguments for the argument
            :type kwds: Any
            """
            self.args = args
            self.kwargs = kwds

    def set_name(self, /, name: str, *, keyword: bool = False) -> None:
        """Set the argument name and destination variable.

        Configures how the argument will be referenced in the parsed arguments object.
        For keyword arguments (--flags), automatically sets the dest parameter.

        :param name: The name/destination for the argument
        :type name: str
        :param keyword: Whether this is a keyword argument (prefixed with --)
        :type keyword: bool
        :raises Warning: If dest parameter is being overwritten
        """
        if not self.args:
            self.args = (f"--{name.replace('_', '-')}",) if keyword else (name,)
        if not keyword:
            return
        if "dest" in self.kwargs and self.kwargs["dest"] != name:  # pragma: no cover
            warnings.warn("dest is overwritten", stacklevel=2)
        self.kwargs["dest"] = name

    def set_default(self, /, default: Any, *, keyword: bool = False) -> None:
        """Set the argument's default value.

        :param default: The default value to set
        :type default: Any
        :param keyword: Whether this is a keyword argument
        :type keyword: bool
        :raises Warning: If default value is being overwritten
        """
        if "default" in self.kwargs and self.kwargs["default"] != default:  # pragma: no cover
            warnings.warn("default value is overwritten", stacklevel=2)
        self.kwargs["default"] = default
        if not keyword:
            self.kwargs["nargs"] = "?"

    def set_nargs(self, /, nargs: Union[int, str, None]) -> None:
        """Set how many arguments this parameter should consume.

        :param nargs: Number of arguments:
            - int: Exact number of arguments
            - "?": 0 or 1 argument
            - "*": 0 or more arguments
            - "+": 1 or more arguments
            - None: Single argument (default)
        :type nargs: Union[int, str, None]
        :raises Warning: If nargs value is being overwritten
        """
        if "nargs" in self.kwargs and self.kwargs["nargs"] != nargs:  # pragma: no cover
            warnings.warn("nargs is overwritten", stacklevel=2)
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
        """Add this argument to an ArgumentParser instance.

        This implements the callable interface that allows Argument instances to be
        used directly with ArgumentParser.add_argument().

        :param parser: The ArgumentParser to modify
        :type parser: ArgumentParser
        :return: The modified ArgumentParser (for method chaining)
        :rtype: ArgumentParser
        """
        parser.add_argument(*self.args, **self.kwargs)
        return parser

    def __eq__(self, value: Any) -> bool:
        if not isinstance(value, self.__class__):
            return False
        return self.args == value.args and self.kwargs == value.kwargs

    __hash__ = object.__hash__

    def __repr__(self) -> str:
        """Generate a developer-friendly string representation of the Argument.

        The representation includes the class name and all argument configuration
        (names/flags and keyword arguments).

        :return: String representation showing argument configuration
        :rtype: str
        """
        return f"{self.__class__.__qualname__}({self.args}, {self.kwargs})"


if TYPE_CHECKING:
    Arg = Annotated
else:
    Arg = Argument


def get_argument(annotation: Any) -> Optional[Argument]:
    """Extract an Argument instance from a type annotation.

    This helper function checks if the annotation is either:
    1. An Argument instance directly
    2. An Annotated type containing an Argument in its metadata

    :param annotation: The type annotation to inspect
    :type annotation: Any
    :return: The extracted Argument if found, None otherwise
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
    """Construct an ArgumentParser from a function's signature and type annotations.

    This function analyzes the function's parameters and their type annotations to
    automatically configure an ArgumentParser. Parameters annotated with `Arg` or
    `Annotated[..., Argument(...)]` will be converted to command-line arguments.

    Key features:
    - Automatically handles positional vs optional arguments based on parameter kind
    - Supports all standard argparse argument types and actions
    - Provides flexible handling of unannotated parameters via unannotated_mode
    - Preserves function docstring as parser description

    :param func: The function or its signature to analyze
    :type func: Union[Callable, Signature]
    :param unannotated_mode: Determines behavior for parameters without Argument metadata:
        - "strict": Raises TypeError (default)
        - "autoconvert": Attempts to infer Argument from type annotation
        - "ignore": Silently skips unannotated parameters
    :type unannotated_mode: Literal["strict", "autoconvert", "ignore"]
    :param parser_factory: Custom factory for creating the parser instance
    :type parser_factory: Callable[..., _T_Parser]
    :return: Fully configured ArgumentParser instance
    :rtype: _T_Parser
    :raises TypeError: For invalid parameter kinds or strict mode violations
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
