import argparse
import sys
from pathlib import Path
from typing import Literal, Tuple
from unittest.mock import patch

import pytest
from typing_extensions import Annotated

from ptcmd.argument import Arg, Argument, IgnoreArg, build_parser, get_argument, invoke_from_argv, invoke_from_ns, entrypoint


def test_argument() -> None:
    arg = Arg[str, "-v", "--version"]
    arg_ins = get_argument(arg)
    assert arg_ins is not None
    assert arg_ins.args == ("-v", "--version")
    assert arg_ins.kwargs == {"type": str}

    arg = Arg[str, "-v", "--version", {}]
    assert get_argument(arg) == arg_ins

    arg = Arg[str, "-v", "--version", Argument(type=str)]
    assert get_argument(arg) == arg_ins

    arg = Annotated[str, Argument("-v", "--version", type=str)]
    assert get_argument(arg) == arg_ins


def test_build_parser() -> None:
    def example(
        path: Arg[str, Argument(help="Input path")],
        timeout: Arg[int, "--timeout"] = 10,  # noqa: F821,B002
        *,
        force: bool = False,
    ) -> None: ...

    parser = build_parser(example, unannotated_mode="autoconvert")
    assert parser.parse_known_args(["/tmp", "--force", "--timeout", "20"])[0].__dict__ == {
        "path": "/tmp",
        "force": True,
        "timeout": 20,
    }

    with pytest.raises(TypeError):
        build_parser(example, unannotated_mode="strict")

    parser = build_parser(example, unannotated_mode="ignore")
    assert parser.parse_known_args(["/tmp", "--force"])[0].__dict__ == {"path": "/tmp", "timeout": 10}

    def example2(
        path: Arg[str, Argument(help="Input path", type=Path)],
        *args: Arg[str, Argument(help="Extra arguments")],
    ) -> None: ...

    parser = build_parser(example2, unannotated_mode="strict")
    assert parser.parse_known_args(["/tmp", "foo", "bar"])[0].__dict__ == {"path": Path("/tmp"), "args": ["foo", "bar"]}


def test_invoke_from_ns() -> None:
    def test_func(arg1: str, *args: str) -> dict:
        return {"arg1": arg1, "args": args}

    # Test with various parameter types
    ns = argparse.Namespace(
        arg1="value1",
        args=["extra1", "extra2"],
    )

    result = invoke_from_ns(test_func, ns)
    assert result["arg1"] == "value1"
    assert result["args"] == ("extra1", "extra2")


def test_invoke_from_argv() -> None:
    def test_func(*args: str, verbose: bool) -> dict:
        return {"args": args, "verbose": verbose}

    result = invoke_from_argv(test_func, ["--verbose", "arg1", "arg2"], unannotated_mode="autoconvert")
    assert result == {"args": ("arg1", "arg2"), "verbose": True}


def test_literal_support() -> None:
    """Test automatic choices extraction from Literal types."""
    # Test with Literal type alone
    arg = Arg[Literal["a", "b", "c"]]
    arg_ins = get_argument(arg)
    assert arg_ins is not None
    assert arg_ins.kwargs.get("choices") == ("a", "b", "c")

    # Test with Literal and flags
    arg = Arg[Literal[0, 1, 2], "-v", "--verbose"]
    arg_ins = get_argument(arg)
    assert arg_ins is not None
    assert arg_ins.args == ("-v", "--verbose")
    assert arg_ins.kwargs.get("choices") == (0, 1, 2)

    # Test with explicit choices that override Literal
    arg = Arg[Literal["x", "y", "z"], "--choice", {"choices": ["x", "y"]}]
    arg_ins = get_argument(arg)
    assert arg_ins is not None
    assert arg_ins.kwargs.get("choices") == ["x", "y"]

    # Test with non-Literal type
    arg = Arg[str, "--name"]
    arg_ins = get_argument(arg)
    assert arg_ins is not None
    assert "choices" not in arg_ins.kwargs


def test_skip_argument() -> None:
    """Test the skip parameter functionality."""
    # Test skip=True
    def func1(arg: Annotated[str, Argument("--skip-true", skip=True)]) -> None:
        pass

    parser = build_parser(func1, unannotated_mode="strict")
    with pytest.raises(SystemExit):  # Should fail as argument is not added
        parser.parse_args(["--skip-true", "value"])

    # Test skip=False
    def func2(arg: Annotated[str, Argument("--skip-false", dest="arg", skip=False)]) -> None:
        pass

    parser = build_parser(func2, unannotated_mode="strict")
    args = parser.parse_args(["--skip-false", "value"])
    assert args.arg == "value"

    # Test default (no skip specified)
    def func3(arg: Annotated[str, Argument("--no-skip", dest="arg")]) -> None:
        pass

    parser = build_parser(func3, unannotated_mode="strict")
    args = parser.parse_args(["--no-skip", "value"])
    assert args.arg == "value"

    # Test skip via Arg annotation
    def func4(arg: Arg[str, "--arg-alias", {"skip": True}]) -> None:  # noqa: F821,B002
        pass

    parser = build_parser(func4, unannotated_mode="strict")
    with pytest.raises(SystemExit):
        parser.parse_args(["--arg-alias", "value"])

    # Test skip with other parameters
    def func5(arg: Annotated[
        str,
        Argument("--combined", skip=True, help="Should be skipped")
    ]) -> None:
        pass

    parser = build_parser(func5, unannotated_mode="strict")
    # Ensure the argument wasn't added
    assert not any(action.option_strings == ["--combined"] for action in parser._actions)

    # Test skip=False removal in __init__
    arg = Argument("--test", skip=False)
    assert "skip" not in arg.kwargs  # Verify skip=False was removed

    # Simple test for IgnoreArg
    def func6(arg: IgnoreArg[str]) -> None:
        pass

    parser = build_parser(func6, unannotated_mode="strict")
    # Should have no arguments besides help
    assert len(parser._actions) == 1  # Only the help action
    assert parser._actions[0].option_strings == ["-h", "--help"]


def test_entrypoint_basic() -> None:
    """Test basic functionality of the entrypoint decorator."""
    @entrypoint(unannotated_mode="autoconvert")
    def main(
        *,
        path: Arg[str, "--path"],  # noqa: F821,B002
        force: bool = False
    ) -> Tuple[str, bool]:
        return path, force

    # Test with explicit argv
    result = main(argv=["--path", "test.txt", "--force"])
    assert result == ("test.txt", True)

    # Test with sys.argv simulation
    with patch.object(sys, 'argv', ['script.py', '--path', 'default.txt']):
        result = main()
        assert result == ("default.txt", False)
