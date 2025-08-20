import asyncio
import io
from typing import Generator
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from prompt_toolkit import PromptSession
from prompt_toolkit.input import create_pipe_input, PipeInput
from prompt_toolkit.output import DummyOutput
from rich.text import Text

from ptcmd import Cmd
from ptcmd.core import CommandInfo


@pytest.fixture
def pipe_input() -> Generator[PipeInput, None, None]:
    """Fixture providing pipe input for testing."""
    with create_pipe_input() as inp:
        yield inp

@pytest.fixture
def cmd(pipe_input: PipeInput) -> Cmd:
    """Fixture providing a BaseCmd instance with mocked stdout and real session."""
    stdout = io.StringIO()
    # Create real PromptSession with pipe input
    session = PromptSession(
        input=pipe_input,
        output=DummyOutput()
    )
    return Cmd(stdout=stdout, session=session)


def test_parseline(cmd: Cmd) -> None:
    """Test command line parsing."""
    # Test basic command
    cmd_name, args, line = cmd.parseline("test arg1 arg2")
    assert cmd_name == "test"
    assert args == ["arg1", "arg2"]
    assert line == "test arg1 arg2"

    # Test shortcut
    cmd_name, args, line = cmd.parseline("? arg1")
    assert cmd_name == "help"
    assert args == ["arg1"]


@pytest.mark.asyncio
async def test_cmdloop_async(cmd: Cmd, pipe_input: PipeInput) -> None:
    """Test async command loop with real input."""
    # Send input command
    pipe_input.send_text("exit\n")

    # Run cmdloop with timeout
    try:
        await asyncio.wait_for(cmd.cmdloop_async(), timeout=1.0)
    except asyncio.TimeoutError:
        pytest.fail("cmdloop_async did not complete within timeout")

@pytest.mark.asyncio
async def test_do_help_no_topic(cmd: Cmd) -> None:
    """Test help command without topic."""
    with patch.object(Cmd, '_help_menu') as mock_help_menu:
        cmd.do_help("")
        mock_help_menu.assert_called_once_with(False)

@pytest.mark.asyncio
async def test_do_help_with_topic(cmd: Cmd) -> None:
    """Test help command with topic."""
    # Create mock command info
    mock_info = MagicMock(spec=CommandInfo)
    mock_info.name = "test_cmd"
    mock_info.help_func = MagicMock(return_value="Test command help")
    cmd.command_info = {"test_cmd": mock_info}  # type: ignore

    with patch.object(Cmd, 'poutput') as mock_poutput:
        cmd.do_help("test_cmd")
        mock_poutput.assert_called_once_with(Text("Test command help"))

@pytest.mark.asyncio
async def test_do_help_verbose(cmd: Cmd) -> None:
    """Test help command with verbose flag."""
    with patch.object(Cmd, '_help_menu') as mock_help_menu:
        cmd.do_help("", verbose=True)
        mock_help_menu.assert_called_once_with(True)

@pytest.mark.asyncio
async def test_do_help_unknown_topic(cmd: Cmd) -> None:
    """Test help command with unknown topic."""
    with patch.object(Cmd, 'perror') as mock_perror:
        cmd.do_help("unknown_cmd")
        mock_perror.assert_called_once_with("Unknown command: unknown_cmd")

@pytest.mark.asyncio
async def test_do_exit(cmd: Cmd) -> None:
    """Test exit command."""
    result = cmd.do_exit([])
    assert result is True

@pytest.mark.asyncio
async def test_do_shell(cmd: Cmd) -> None:
    """Test shell command execution."""
    with patch.object(asyncio, "create_subprocess_shell") as mock_subprocess:
        mock_process = MagicMock()
        mock_process.wait = AsyncMock(return_value=0)
        mock_subprocess.return_value = mock_process
        await cmd.do_shell(["echo", "hello"])
        mock_subprocess.assert_called_once_with("echo hello", stdin=None, stdout=cmd.stdout, stderr=cmd.stdout)

    with patch.object(asyncio, "create_subprocess_shell") as mock_subprocess:
        mock_process = MagicMock()
        mock_process.wait = AsyncMock(return_value=0)
        mock_subprocess.return_value = mock_process
        await cmd.do_shell([])
        mock_subprocess.assert_called_once_with("", stdin=None, stdout=cmd.stdout, stderr=cmd.stdout)

def test_help_menu_categorized(cmd: Cmd) -> None:
    """Test categorized help menu output."""
    # Create command info with categories
    cmd1 = MagicMock(spec=CommandInfo)
    cmd1.name = "cmd1"
    cmd1.category = "Category1"
    cmd1.hidden = False
    cmd1.disabled = False
    cmd1.cmd_func = MagicMock(__doc__="Command 1 help")
    cmd1.argparser = None
    cmd1.help_func = None

    cmd2 = MagicMock(spec=CommandInfo)
    cmd2.name = "cmd2"
    cmd2.category = "Category2"
    cmd2.hidden = False
    cmd2.disabled = False
    cmd2.cmd_func = MagicMock(__doc__="Command 2 help")
    cmd2.argparser = None
    cmd2.help_func = None

    # Set command info
    cmd.command_info = {"cmd1": cmd1, "cmd2": cmd2}  # type: ignore

    # Capture output using console capture
    with cmd.console.capture() as capture:
        cmd._help_menu()
    output = capture.get()

    # Check for category headers
    assert "Category1" in output
    assert "Category2" in output

    # Check for command names
    assert "cmd1" in output
    assert "cmd2" in output

    # Note: When verbose=False (default), command descriptions are not shown
    # The test is checking the basic categorized help menu functionality
