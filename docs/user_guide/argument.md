# Argument Parsing

The argument parsing system provides functionality to build `ArgumentParser` from function signatures. This is a relatively independent component that integrates with the command component class `Command` to enter the `ptcmd` framework.

## Basic Example

Using the `@auto_argument` decorator is the simplest declarative way to handle argument parsing. It automatically analyzes the function's parameter signature and creates the corresponding `ArgumentParser` instance:

```python linenums="1"
from ptcmd import Cmd, auto_argument

class MyApp(Cmd):
    @auto_argument
    def do_hello(self, name: str = "World") -> None:
        """Hello World!"""
        self.poutput(f"Hello, {name}!")
```

In the example above, the `name` parameter is automatically converted to an optional positional argument with a default value of "World".

## Argument Class

`Argument` is the core class of the argument parsing system, used to declaratively define command-line arguments. It encapsulates `argparse` parameter configurations, providing a more Pythonic interface.

### Basic Usage

You can directly instantiate `Argument` to define parameters:

```python linenums="1"
from ptcmd import Argument

# Create a simple string parameter
file_arg = Argument(
    "--file", 
    type=str,
    help="Input file path"
)

# Create a boolean flag parameter
verbose_arg = Argument(
    "-v", "--verbose",
    action="store_true",
    help="Enable verbose output"
)
```

### Parameter Configuration

`Argument` supports all standard `argparse` parameter configurations. Common parameters include:

| Parameter | Description | Example |
|-----------|-------------|---------|
| `action` | Specifies parameter action | `action="store_true"` |
| `nargs` | Number of parameter values | `nargs='*'` |
| `const` | Constant value used with `nargs` or `action` | `const="value"` |
| `default` | Default value | `default=0` |
| `type` | Parameter type conversion function | `type=int` |
| `choices` | Allowed parameter values | `choices=["a", "b"]` |
| `required` | Whether parameter is required | `required=True` |
| `help` | Help text | `help="Input file path"` |
| `metavar` | Parameter name displayed in help message | `metavar="FILE"` |
| `dest` | Target attribute name for storing parameter value | `dest="output_file"` |
| `version` | Version number used with `action="version"` | `version="1.0.0"` |

For example, defining a parameter that requires multiple input files:

```python linenums="1"
files: Arg[
    list,
    "--files",
    {"nargs": "*", "type": str, "help": "List of input files"}
]
```

## Using Arg Type Annotations

For more complex parameter definitions, you can use `Arg` type hints. `Arg` allows specifying parameter flags, help text, and other attributes:

```python linenums="1"
from ptcmd import Cmd, Arg, auto_argument

class MathApp(Cmd):
    @auto_argument
    def do_add(
        self, 
        x: float, 
        y: float,
        *,
        verbose: Arg[bool, "-v", "--verbose", {"help": "Verbose output"}] = False
    ) -> None:
        """Add two numbers"""
        result = x + y
        if verbose:
            self.poutput(f"{x} + {y} = {result}")
        else:
            self.poutput(result)
```

The syntax for `Arg` is: `Arg[Type, parameter flags..., {parameter attributes}]`

- Type: Data type of the parameter (e.g., `str`, `int`, `float`, `bool`)
- Parameter flags: Command-line flags for the parameter (e.g., `"-v"`, `"--verbose"`)
- Parameter attributes: A dictionary containing other parameter attributes (e.g., `help`, `choices`), or an `Argument` instance can be used as attributes.

!!! note

    `Arg` is essentially a simple conversion for type checkers and is functionally equivalent to the `Argument` class at runtime. However, `Arg` is typically recommended only for type annotations.

## Using Annotated and Argument Type Annotations

If you want to strictly adhere to code style checkers, you can use standard `Annotated` and `Argument` to avoid syntax errors with `Arg`:

```python linenums="1"
from typing import Annotated
from ptcmd import Cmd, Argument, auto_argument

class MathApp(Cmd):
    @auto_argument
    def do_add(
        self, 
        x: float, 
        y: float,
        *,
        verbose: Annotated[bool, Argument("-v", "--verbose", action="store_true")] = False
    ) -> None:
        """Add two numbers"""
        result = x + y
        if verbose:
            self.poutput(f"{x} + {y} = {result}")
        else:
            self.poutput(result)
```

However, parameters defined this way won't benefit from parameter field completion, requiring you to specify all necessary fields in the `Argument`.

### Parameter Ignoring

When certain parameters shouldn't appear in the command-line interface, you can use the `IgnoreArg` type to mark that the parameter should be ignored:

```python linenums="1"
from ptcmd import Cmd, IgnoreArg, auto_argument

class App(Cmd):
    @auto_argument
    def do_process(
        self,
        input: str,
        internal_state: IgnoreArg[dict] = {}
    ) -> None:
        """Process input data; internal_state is only for internal state management"""
        # internal_state will not appear in command-line arguments
        self.poutput(f"Processing {input}")
```

In this example, the `internal_state` parameter will be completely ignored and not added to the command-line parser.

## Argument Parsing

`ptcmd` automatically infers parameter behavior based on the parameter's type and position:

1. Positional arguments: Function positional parameters are converted to command-line positional arguments
2. Optional arguments: Keyword arguments separated by `*` are converted to optional arguments
3. Boolean parameters: Parameters of type `bool` are automatically converted to flag arguments (`store_true` or `store_false`)
4. Default values: Parameter default values are passed to `ArgumentParser`

### Automatic Inference

Argument parsing can automatically infer appropriate `argparse` configurations based on type annotations and parameter characteristics, reducing manual configuration. Below are key automatic inference rules:

#### Boolean Type Automatic Conversion

The system automatically selects `store_true` or `store_false` actions based on the default value of boolean parameters:

```python linenums="1"
# Default value is False -> automatically uses store_true
verbose: Arg[bool] = False  
# Generates: parser.add_argument("--verbose", action="store_true")

# Default value is True -> automatically uses store_false
enabled: Arg[bool] = True   
# Generates: parser.add_argument("--enabled", action="store_false")

# Can also specify flags explicitly
debug: Arg[bool, "-d", "--debug"] = False
# Generates: parser.add_argument("-d", "--debug", action="store_true")
```

#### Positional vs. Keyword Parameter Handling

The system automatically determines whether parameters are positional or optional based on their position in the function signature:

```python linenums="1"
@auto_argument
def do_process(
    self,
    input_file: str,      # Positional parameter (no default value)
    output: str = "out",  # Positional parameter (with default value)
    *,
    verbose: bool = False # Keyword parameter -> optional parameter
) -> None:
    pass
```

- Positional parameters: Positional parameters in function signatures (without `*` separator) become command-line positional parameters
- Optional parameters: Keyword parameters separated by `*` become command-line optional parameters (must use `--` prefix)

#### Literal Type Smart Handling

When parameter type is `Literal`, the system automatically sets `choices` and adjusts parameter behavior as needed:

```python linenums="1"
from typing import Literal

# Automatically sets choices
level: Literal["debug", "info", "warning", "error"]

# Combined with default value
level: Literal["debug", "info", "warning", "error"] = "info"
# Generates: parser.add_argument("--level", choices=..., default="info")

# Combined with keyword parameter (automatically becomes optional parameter)
def do_set(
    self,
    *,
    level: Literal["debug", "info"] = "info"
) -> None:
    pass
# Generates: parser.add_argument("--level", ...)
```

Note that if `choices` is explicitly specified in `Argument`, it will override the options automatically derived from `Literal` type:

#### Default Value Handling

Default values directly affect parameter behavior:

```python linenums="1"
# Positional parameter with default value -> becomes optional positional parameter
def do_example(self, file: str = "default.txt") -> None:
    pass
# Generates: parser.add_argument("file", nargs="?", default="default.txt")

# Keyword parameter with default value -> standard optional parameter
def do_example(self, *, count: int = 1) -> None:
    pass
# Generates: parser.add_argument("--count", type=int, default=1)
```

### Handling Unannotated Parameters

When function parameters are not annotated with `Arg` or `Argument`, `build_parser` provides three handling modes controlled by the `unannotated_mode` parameter:

- **strict**: Strict mode, raises `TypeError` when encountering unannotated parameters
- **autoconvert**: Automatic conversion mode, attempts to infer parameter configuration based on type annotations
- **ignore**: Ignore mode, skips unannotated parameters

The `@auto_argument` decorator defaults to **autoconvert** mode. In automatic inference mode, unannotated parameters `x: Tp` are treated as `x: Arg[Tp]` to automatically infer parameter information.

```python linenums="1"
@auto_argument(unannotated_mode="autoconvert")
def do_convert(self, x: int, *, y: str = "y") -> None:
    ...
```

In `autoconvert` mode, the above code is treated as:

```python linenums="1"
@auto_argument(unannotated_mode="autoconvert")
def do_convert(self, x: Arg[int], *, y: Arg[str] = "y") -> None:
    ...
```

After automatic parameter inference, the code is ultimately converted to:

```python linenums="1"
@auto_argument(unannotated_mode="autoconvert")
def do_convert(self, x: Annotated[int, Argument("x", type=int)], *, y: Annotated[str, Argument("-y", type=str, default="y")] = "y") -> None:
    ...
```

## Standalone Argument Parsing

The argument parsing system provides a series of standalone functions for independent use of argument parsing functionality. The simplest way is to use the `entrypoint` decorator:

```python linenums="1"
from ptcmd.argument import entrypoint

@entrypoint
def main(
    x: int,
    *,
    y: str = "y"
) -> None:
    ...

if __name__ == "__main__":
    main()  # Parse arguments from sys.argv and run
