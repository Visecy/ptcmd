import io
from typing import Generator
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from prompt_toolkit.input import PipeInput, create_pipe_input
from prompt_toolkit.output import DummyOutput
from prompt_toolkit.shortcuts import PromptSession

from ptcmd.core import BaseCmd, CommandInfo


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
    session = PromptSession(
        input=pipe_input,
        output=DummyOutput()
    )
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
    with patch.object(base_cmd.console, 'print_exception') as mock_print:
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
