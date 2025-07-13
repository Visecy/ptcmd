import argparse
from argparse import _SubParsersAction
import sys
from types import MethodType
from typing import Any, Optional
from unittest.mock import MagicMock

import pytest

from ptcmd.argument import Arg
from ptcmd.command import Command, auto_argument
from ptcmd.core import BaseCmd, Cmd
from ptcmd.info import CommandInfo, get_cmd_ins


@pytest.fixture
def base_cmd() -> BaseCmd:
    base_cmd = MagicMock(spec=BaseCmd)
    base_cmd.stdin = sys.stdin
    base_cmd.stdout = sys.stdout
    base_cmd.COMMAND_FUNC_PREFIX = "do_"
    return base_cmd


def test_command_init() -> None:
    """Test Command initialization with different parameters."""
    # Test with basic function
    def func(self: Any) -> None:
        pass

    cmd = Command(func)
    assert cmd.__func__ == func
    assert cmd.cmd_name is None
    assert cmd.parser is not None
    assert not cmd.hidden
    assert not cmd.disabled

    # Test with custom name and flags
    cmd = Command(func, cmd_name="custom", hidden=True, disabled=True)
    assert cmd.cmd_name == "custom"
    assert cmd.hidden
    assert cmd.disabled


def test_command_with_parser() -> None:
    """Test Command with custom parser."""
    def func(self: Any) -> None:
        pass

    parser = argparse.ArgumentParser()
    parser.add_argument("--test")
    cmd = Command(func, parser=parser)
    assert cmd.parser == parser


def test_add_subcommand() -> None:
    """Test adding subcommands to a Command."""
    def main_func(self: Any) -> None:
        pass

    def sub_func(self: Any) -> None:
        pass

    main_cmd = Command(main_func)

    # Test with decorator style
    @main_cmd.add_subcommand("sub1")
    def sub1(self: Any) -> None:
        pass

    assert isinstance(sub1, Command)
    assert sub1._parent == main_cmd

    # Test with direct function
    sub2 = main_cmd.add_subcommand("sub2", sub_func)
    assert isinstance(sub2, Command)
    assert sub2._parent == main_cmd
    # assert sub2.cmd_name == "sub2"


def test_invoke_from_argv(base_cmd: BaseCmd) -> None:
    """Test invoking a command from command line arguments."""
    def test_func(self: Any, arg1: str, *, flag: bool = False) -> str:
        return f"arg1={arg1}, flag={flag}"

    cmd_obj = Command(test_func)
    # Test with positional arg
    result = cmd_obj.invoke_from_argv(base_cmd, ["value1"])
    assert result == "arg1=value1, flag=False"

    # Test with flag
    result = cmd_obj.invoke_from_argv(base_cmd, ["value2", "--flag"])
    assert result == "arg1=value2, flag=True"

    # Test with invalid args (should return None due to SystemExit)
    result = cmd_obj.invoke_from_argv(base_cmd, [])
    assert result is None


def test_invoke_from_ns(base_cmd: BaseCmd) -> None:
    """Test invoking a command from a namespace."""
    def test_func(self: Any, arg1: str, flag: bool = False) -> str:
        return f"arg1={arg1}, flag={flag}"

    cmd_obj = Command(test_func)
    # Create namespace
    ns = argparse.Namespace(arg1="test_value", flag=True)
    ns.__cmd_ins__ = cmd_obj

    result = cmd_obj.invoke_from_ns(base_cmd, ns)
    assert result == "arg1=test_value, flag=True"


def test_descriptor_protocol() -> None:
    """Test the descriptor protocol (__get__ method)."""
    assert isinstance(Cmd.do_help, Command)
    assert isinstance(Cmd().do_help, MethodType)
    assert Cmd.do_help.__func__ is Cmd().do_help.__func__


def test_cmd_info(base_cmd: BaseCmd) -> None:
    """Test the __cmd_info__ method."""
    def do_test(self: Any) -> None:
        pass

    command = Command(do_test)
    assert get_cmd_ins(command.parser) is None

    info = command.__cmd_info__(base_cmd)
    assert isinstance(info, CommandInfo)
    assert info.name == "test"  # Stripped "do_" prefix
    assert info.argparser is not None
    assert info.argparser.prog == "test"
    assert get_cmd_ins(info.argparser) is base_cmd
    assert info.completer is not None


def test_call_method() -> None:
    """Test the __call__ method."""
    def func(arg1: str, arg2: int) -> str:
        return f"{arg1} {arg2}"

    cmd = Command(func)
    result = cmd("hello", 42)
    assert result == "hello 42"


def test_auto_argument_basic() -> None:
    """Test basic auto_argument functionality."""
    @auto_argument
    def do_test(self: Any, arg1: str, flag: bool = False) -> str:
        return f"{arg1} {flag}"

    assert isinstance(do_test, Command)
    assert do_test.parser is not None

    # Check that the parser has the expected arguments
    actions = do_test.parser._actions
    arg_names = [a.dest for a in actions if a.dest != "help"]
    assert "arg1" in arg_names
    assert "flag" in arg_names


def test_auto_argument_with_arg_annotation() -> None:
    """Test auto_argument with Arg annotations."""
    @auto_argument
    def do_test(
        self: Any,
        name: Arg[str, "-n", "--name", {"help": "Name argument"}],  # noqa: F821,B002,F722
        count: Arg[int, "-c", "--count"] = 1,  # noqa: F821,B002
        verbose: Arg[bool] = False  # type: ignore
    ) -> None:
        pass

    assert isinstance(do_test, Command)

    # Check parser arguments
    parser = do_test.parser
    args = {a.dest: a for a in parser._actions if a.dest != "help"}

    assert "name" in args
    assert "-n" in args["name"].option_strings
    assert "--name" in args["name"].option_strings
    assert args["name"].help == "Name argument"

    assert "count" in args
    assert "-c" in args["count"].option_strings
    assert "--count" in args["count"].option_strings
    assert args["count"].default == 1

    assert "verbose" in args


def test_auto_argument_with_parameters() -> None:
    """Test auto_argument with parameters."""
    @auto_argument(hidden=True, disabled=True)
    def do_test(self: Any, arg: str) -> None:
        pass

    assert isinstance(do_test, Command)
    assert do_test.hidden
    assert do_test.disabled


def test_auto_argument_with_custom_parser() -> None:
    """Test auto_argument with a custom parser."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--custom")

    @auto_argument(parser=parser)
    def do_test(self: Any) -> None:
        pass

    assert isinstance(do_test, Command)
    assert do_test.parser is parser

    # Verify the custom argument exists
    args = {a.dest: a for a in parser._actions if a.dest != "help"}
    assert "custom" in args


@pytest.mark.asyncio
async def test_command_in_basecmd() -> None:
    """Test Command integration with BaseCmd."""
    class TestCmd(BaseCmd):
        @auto_argument
        def do_greet(self, name: str = "World") -> None:
            self.output = f"Hello, {name}!"

        @auto_argument
        def do_add(
            self,
            a: Arg[int, "-a"],  # noqa: F821,B002
            b: Arg[int, "-b"]  # noqa: F821,B002
        ) -> None:
            self.output = f"Result: {a + b}"

    # Create instance with output capture
    cmd = TestCmd()
    cmd.output = ""

    # Test command execution
    await cmd.onecmd("greet Alice")
    assert cmd.output == "Hello, Alice!"

    await cmd.onecmd("add -a 5 -b 7")
    assert cmd.output == "Result: 12"


@pytest.mark.asyncio
async def test_subcommands() -> None:
    """Test subcommands in a Cmd instance."""
    class TestCmd(Cmd):
        def __init__(self) -> None:
            super().__init__()
            self.output = ""

        @auto_argument
        def do_main(self, *, arg: Optional[str] = None) -> None:
            self.output = f"Main command: {arg}"

        main_cmd = do_main

        @main_cmd.add_subcommand("sub")
        def main_sub(self, arg: Optional[str] = None) -> None:
            self.output = f"Subcommand: {arg}"

    cmd = TestCmd()

    # Test subcommand
    await cmd.onecmd("main sub subarg")
    assert cmd.output == "Subcommand: subarg"


def test_ensure_subparsers_with_existing() -> None:
    """Test _ensure_subparsers when subparsers already exist."""
    def func(self: Any) -> None:
        pass

    cmd = Command(func)

    # First call creates the subparsers action
    action1 = cmd._ensure_subparsers()
    # Second call should return the same instance
    action2 = cmd._ensure_subparsers()
    assert action1 is action2


def test_completer_getter(base_cmd: BaseCmd) -> None:
    """Test custom completer getter assignment."""
    def func(self: Any) -> None:
        pass

    cmd = Command(func, cmd_name="test")
    mock_completer = MagicMock()

    @cmd.completer_getter
    def get_completer(cmd: BaseCmd) -> Any:
        return mock_completer

    assert cmd._completer_getter is get_completer

    info = cmd.__cmd_info__(base_cmd)
    assert info.name == "test"
    assert info.completer is mock_completer


def test_add_subcommand_with_aliases() -> None:
    """Test adding subcommand with aliases."""
    def main_func(self: Any) -> None:
        pass

    def sub_func(self: Any) -> None:
        pass

    main_cmd = Command(main_func)
    main_cmd.add_subcommand("sub", sub_func, aliases=["s", "sb"])

    # Check that the parser for the subcommand has the aliases
    subparsers_action = main_cmd.parser._actions[-1]
    assert isinstance(subparsers_action, _SubParsersAction)
    # Check that aliases are present in the choices
    assert "s" in subparsers_action.choices
    assert "sb" in subparsers_action.choices
    # The main command should be present too
    assert "sub" in subparsers_action.choices


@pytest.mark.asyncio
async def test_disabled_command() -> None:
    """Test that a disabled command is not executable."""

    class TestCmd(BaseCmd):
        @auto_argument(disabled=True)
        def do_disabled_cmd(self) -> None:
            self.poutput("This should not run")

        def default(self, line: str) -> None:
            self.unknown_command = True

    cmd = TestCmd()
    # Try to execute the disabled command
    await cmd.onecmd("disabled_cmd")
    # Since the command is disabled, it should show unknown command
    assert cmd.unknown_command
