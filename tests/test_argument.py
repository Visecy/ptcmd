import argparse
from pathlib import Path

import pytest
from typing_extensions import Annotated

from ptcmd.argument import Arg, Argument, build_parser, get_argument, invoke_from_argv, invoke_from_ns


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
