import io
from typing import Generator
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from prompt_toolkit.input import PipeInput, create_pipe_input
from prompt_toolkit.output import DummyOutput
from prompt_toolkit.shortcuts import PromptSession
from rich.text import Text

from ptcmd.core import BaseCmd, Cmd, CommandInfo


@pytest.fixture
def pipe_input() -> Generator[PipeInput, None, None]:
    """Fixture providing pipe input for testing."""
    with create_pipe_input() as inp:
        yield inp


@pytest.fixture
def base_cmd(pipe_input: PipeInput) -> BaseCmd:
    """Fixture providing a BaseCmd instance with mocked stdout and real session."""
    stdout = io.StringIO()
    # Create real PromptSession with pipe input
    session = PromptSession(input=pipe_input, output=DummyOutput())
    return BaseCmd(stdout=stdout, session=session)


def test_init(base_cmd: BaseCmd) -> None:
    assert base_cmd.stdout is not None
    assert not base_cmd.command_info


@pytest.mark.asyncio
async def test_onecmd(base_cmd: BaseCmd) -> None:
    """Test command execution."""
    # Mock command info
    mock_info = MagicMock(spec=CommandInfo)
    mock_info.name = "test"
    mock_info.disabled = False
    mock_info.cmd_func = AsyncMock(return_value=None)
    base_cmd.command_info = {"test": mock_info}  # type: ignore

    result = await base_cmd.onecmd("test arg1 arg2")
    mock_info.cmd_func.assert_called_once_with(["arg1", "arg2"])
    assert result is None


@pytest.mark.asyncio
async def test_input_line(base_cmd: BaseCmd, pipe_input: PipeInput) -> None:
    """Test input line handling with real input."""
    pipe_input.send_text("test input\n")
    result = await base_cmd.input_line()
    assert result == "test input"


def test_pexcept(base_cmd: BaseCmd) -> None:
    """Test exception printing."""
    with patch.object(base_cmd.console, "print_exception") as mock_print:
        try:
            raise ValueError("Test error")
        except Exception:
            base_cmd.pexcept()
        mock_print.assert_called_once()


@pytest.mark.asyncio
async def test_cmd_queue(base_cmd: BaseCmd) -> None:
    """Test command queue execution."""
    base_cmd.cmdqueue = ["cmd1", "cmd2", "EOF"]
    mock_info = MagicMock(spec=CommandInfo)
    mock_info.name = "cmd1"
    mock_info.disabled = False
    mock_info.cmd_func = AsyncMock(return_value=None)
    base_cmd.command_info = {"cmd1": mock_info, "cmd2": mock_info}  # type: ignore

    await base_cmd.cmdloop_async()
    assert mock_info.cmd_func.call_count == 2
    assert base_cmd.cmdqueue == []


def test_poutput(base_cmd: BaseCmd) -> None:
    """Test output methods."""
    base_cmd.poutput("test message")
    assert "test message" in base_cmd.stdout.getvalue()  # type: ignore


def test_perror(base_cmd: BaseCmd) -> None:
    """Test error output."""
    base_cmd.perror("error message")
    output = base_cmd.stdout.getvalue()  # type: ignore
    assert "error message" in output


def test_help_system(base_cmd: BaseCmd) -> None:
    """Test help system methods."""
    # Create mock command info objects
    cmd1 = MagicMock()
    cmd1.name = "cmd1"
    cmd1.hidden = False
    cmd1.disabled = False

    cmd2 = MagicMock()
    cmd2.name = "cmd2"
    cmd2.hidden = True
    cmd2.disabled = False

    base_cmd.command_info = {"cmd1": cmd1, "cmd2": cmd2}  # type: ignore
    visible = base_cmd.get_visible_commands()
    assert visible == ["cmd1"]


def test_init_non_tty() -> None:
    """Test initialization when stdin is not a TTY."""
    # Simulate non-TTY by using a StringIO that returns False for isatty
    non_tty_stdin = io.StringIO()
    non_tty_stdout = io.StringIO()
    cmd = BaseCmd(stdin=non_tty_stdin, stdout=non_tty_stdout)
    assert cmd.stdin == non_tty_stdin
    assert cmd.stdout == non_tty_stdout
    assert cmd.raw_stdout == non_tty_stdout
    assert cmd.session is None


@pytest.mark.asyncio
async def test_emptyline(base_cmd: BaseCmd) -> None:
    """Test empty line input."""
    # When there is no last command, empty line should do nothing
    base_cmd.lastcmd = ""
    result = await base_cmd.emptyline()
    assert result is None

    # When there is a last command, it should be repeated
    base_cmd.lastcmd = "last_command"
    # Patch the onecmd method at the class level
    with patch.object(BaseCmd, "onecmd", new_callable=AsyncMock) as mock_onecmd:
        mock_onecmd.return_value = None
        result = await base_cmd.emptyline()
        mock_onecmd.assert_awaited_once_with("last_command")
        assert result is None


@pytest.mark.asyncio
async def test_default(base_cmd: BaseCmd) -> None:
    """Test default method for unknown commands."""
    # Test unknown command
    with patch.object(BaseCmd, "perror") as mock_perror:
        result = await base_cmd.default("unknown_command")
        mock_perror.assert_called_once_with("Unknown command: unknown_command")
        assert result is None

    # Test EOF
    result = await base_cmd.default("EOF")
    assert result is True


def test_parseline_shortcuts(base_cmd: BaseCmd) -> None:
    """Test command line parsing with shortcuts."""
    # Setup shortcuts and mock command info
    base_cmd.shortcuts = {"?": "help", "!": "shell"}
    # Create a mock CommandInfo object to satisfy type checking
    mock_info = MagicMock(spec=CommandInfo)
    mock_info.name = "help"
    base_cmd.command_info = {"help": mock_info}  # type: ignore

    # Test valid shortcut
    cmd, args, line = base_cmd.parseline("?topic")
    assert cmd == "help"
    assert args == ["topic"]
    assert line == "help topic"

    # Test empty command
    cmd, args, line = base_cmd.parseline("")
    assert cmd is None
    assert args is None
    assert line == ""

    # Test invalid shortcut
    base_cmd.shortcuts = {"@": "unknown"}
    cmd, args, line = base_cmd.parseline("@test")
    assert cmd is None
    assert args is None
    assert line == "@test"


def test_render_rich_text(base_cmd: BaseCmd) -> None:
    """Test rich text rendering."""
    # Test string input
    text = "Hello, World!"
    rendered = base_cmd._render_rich_text(text)
    assert rendered == text

    text = [("", "Formatted")]
    rendered = base_cmd._render_rich_text(text)
    assert rendered == text

    # Test formatted text (mock console capture)
    with patch.object(base_cmd.console, "capture") as mock_capture:
        # Create a mock context manager
        mock_context = MagicMock()
        mock_context.__enter__.return_value.get.return_value = "Formatted"
        mock_capture.return_value = mock_context

        # The method should capture the formatted text and return it
        result = base_cmd._render_rich_text(Text("Hello World!"))
        assert result == "Formatted"

    # Test plain string input
    text = "Plain text"
    rendered = base_cmd._render_rich_text(text)
    assert rendered == text


def test_repr(base_cmd: BaseCmd) -> None:
    """Test string representation."""
    base_cmd.prompt = "test_prompt"
    base_cmd.shortcuts = {"?": "help"}
    base_cmd.command_info = {"help": MagicMock(), "exit": MagicMock()}  # type: ignore
    rep = repr(base_cmd)
    assert "BaseCmd" in rep
    assert "commands=2" in rep
    assert "prompt='test_prompt'" in rep
    assert "shortcuts={'?': 'help'}" in rep


def test_inherit_default_prefix() -> None:
    """Test subclass inherits default prefix without conflict."""

    class SubCmd(BaseCmd):
        pass

    # The default prefix should be the same as the base class
    assert SubCmd.COMMAND_FUNC_PREFIX == BaseCmd.COMMAND_FUNC_PREFIX
    # The __commands__ set should be a copy, not the same object
    assert SubCmd.__commands__ is not BaseCmd.__commands__


def test_change_prefix_no_conflict() -> None:
    """Test changing prefix to one that doesn't conflict with parent."""

    class SubCmd(BaseCmd):
        COMMAND_FUNC_PREFIX = "new_"

    # The prefix should be changed
    assert SubCmd.COMMAND_FUNC_PREFIX == "new_"
    # The __commands__ set should be empty because we changed the prefix
    assert len(SubCmd.__commands__) == 0


def test_change_prefix_with_conflict() -> None:
    """Test changing prefix to one that conflicts with parent."""
    with pytest.raises(ValueError, match="Cannot override command prefix: parent prefix .* conflicts with subclass prefix .*"):

        class SubCmd(Cmd):
            COMMAND_FUNC_PREFIX = "do"  # This is a prefix of the parent's "do_"


def test_command_collection_after_prefix_change() -> None:
    """Test command collection works correctly after changing prefix."""

    class SubCmd(BaseCmd):
        COMMAND_FUNC_PREFIX = "custom_"

        def custom_test(self) -> None:
            pass

    # The command should be collected
    assert len(SubCmd.__commands__) == 1
    assert SubCmd.custom_test in SubCmd.__commands__


def test_command_collection_with_same_prefix() -> None:
    """Test command collection when using same prefix as parent."""

    class SubCmd(BaseCmd):
        COMMAND_FUNC_PREFIX = "do_"

        def do_test(self) -> None:
            pass

    # The command should be collected
    assert len(SubCmd.__commands__) == 1
    assert SubCmd.do_test in SubCmd.__commands__


def test_multiple_inheritance_with_conflicting_prefixes() -> None:
    """Test when subclass inherits from multiple BaseCmd with conflicting prefixes."""

    # Create two base classes with different prefixes
    class BaseA(BaseCmd):
        COMMAND_FUNC_PREFIX = "a_"

    class BaseB(BaseCmd):
        COMMAND_FUNC_PREFIX = "b_"

    # Try to create a subclass from both
    with pytest.raises(TypeError, match="All BaseCmd parent classes must have the same COMMAND_FUNC_PREFIX"):

        class SubCmd(BaseA, BaseB):
            pass


def test_prefix_change_with_existing_commands() -> None:
    """Test changing prefix when class already has commands."""

    # Create base class with a command
    class BaseWithCommand(BaseCmd):
        def do_test(self) -> None:
            pass

    # Create subclass that changes prefix
    with pytest.warns(RuntimeWarning, match="Command prefix changed from 'do_' to 'new_'"):

        class SubCmd(BaseWithCommand):
            COMMAND_FUNC_PREFIX = "new_"

    # Commands should be cleared
    assert len(SubCmd.__commands__) == 0


def test_command_collection_with_prefix() -> None:
    """Test command collection for methods starting with prefix."""

    class SubCmd(BaseCmd):
        COMMAND_FUNC_PREFIX = "cmd_"

        def cmd_test(self) -> None:
            pass

        def not_a_command(self) -> None:
            pass

        def cmd_another(self) -> None:
            pass

    # Only methods with cmd_ prefix should be collected
    assert len(SubCmd.__commands__) == 2
    assert SubCmd.cmd_test in SubCmd.__commands__
    assert SubCmd.cmd_another in SubCmd.__commands__
    assert SubCmd.not_a_command not in SubCmd.__commands__
