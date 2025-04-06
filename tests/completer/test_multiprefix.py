from unittest.mock import MagicMock

import pytest
from prompt_toolkit.document import Document

from ptcmd.completer import MultiPrefixCompleter


@pytest.fixture
def mock_completer() -> MagicMock:
    """Fixture providing a mock completer that returns fixed completions."""
    completer = MagicMock()
    completer.get_completions.return_value = [
        MagicMock(text="completion1", display="display1"),
        MagicMock(text="completion2", display="display2")
    ]
    return completer

def test_multi_prefix_completer_with_matching_prefix(mock_completer: MagicMock) -> None:
    """Test MultiPrefixCompleter with matching prefix."""
    shortcuts = {
        "git ": mock_completer,
        "docker ": mock_completer
    }
    completer = MultiPrefixCompleter(shortcuts, default=None)  # type: ignore

    # Test with matching git prefix
    doc = Document("git status", cursor_position=10)
    completions = list(completer.get_completions(doc, None))
    assert len(completions) == 2
    mock_completer.get_completions.assert_called_once()

    # Test with matching docker prefix
    mock_completer.reset_mock()
    doc = Document("docker ps", cursor_position=8)
    completions = list(completer.get_completions(doc, None))
    assert len(completions) == 2
    mock_completer.get_completions.assert_called_once()

def test_multi_prefix_completer_with_non_matching_prefix(mock_completer: MagicMock) -> None:
    """Test MultiPrefixCompleter with non-matching prefix."""
    shortcuts = {
        "git ": mock_completer,
        "docker ": mock_completer
    }
    completer = MultiPrefixCompleter(shortcuts, default=None)  # type: ignore

    # Test with non-matching prefix
    doc = Document("other command", cursor_position=12)
    completions = list(completer.get_completions(doc, None))
    assert len(completions) == 0
    mock_completer.get_completions.assert_not_called()

def test_multi_prefix_completer_with_default(mock_completer: MagicMock) -> None:
    """Test MultiPrefixCompleter with default completer."""
    default_completer = MagicMock()
    default_completer.get_completions.return_value = [
        MagicMock(text="default1", display="default1")
    ]

    shortcuts = {
        "git ": mock_completer
    }
    completer = MultiPrefixCompleter(shortcuts, default=default_completer)  # type: ignore

    # Test with non-matching prefix should use default
    doc = Document("other command", cursor_position=12)
    completions = list(completer.get_completions(doc, None))
    assert len(completions) == 1
    assert completions[0].text == "default1"
    default_completer.get_completions.assert_called_once()
    mock_completer.get_completions.assert_not_called()

def test_multi_prefix_completer_with_none_completer(mock_completer: MagicMock) -> None:
    """Test MultiPrefixCompleter with None completer for a prefix."""
    shortcuts = {
        "git ": mock_completer,
        "none ": None
    }
    completer = MultiPrefixCompleter(shortcuts, default=None)  # type: ignore

    # Test with prefix that has None completer
    doc = Document("none command", cursor_position=12)
    completions = list(completer.get_completions(doc, None))
    assert len(completions) == 0
    mock_completer.get_completions.assert_not_called()

def test_multi_prefix_completer_with_partial_match(mock_completer: MagicMock) -> None:
    """Test MultiPrefixCompleter with partial prefix match."""
    shortcuts = {
        "git ": mock_completer,
        "github ": mock_completer
    }
    completer = MultiPrefixCompleter(shortcuts, default=None)  # type: ignore

    # Test with partial match (should not match)
    doc = Document("gi", cursor_position=2)
    completions = list(completer.get_completions(doc, None))
    assert len(completions) == 0
    mock_completer.get_completions.assert_not_called()

def test_multi_prefix_completer_document_adjustment(mock_completer: MagicMock) -> None:
    """Test MultiPrefixCompleter properly adjusts the document."""
    shortcuts = {
        "git ": mock_completer
    }
    completer = MultiPrefixCompleter(shortcuts, default=None)  # type: ignore

    # Test document adjustment
    doc = Document("git status", cursor_position=8)  # cursor after "git sta"
    _ = list(completer.get_completions(doc, None))  # Ignore unused completions

    # Verify mock was called with adjusted document
    mock_completer.get_completions.assert_called_once()
    called_doc = mock_completer.get_completions.call_args[0][0]
    assert called_doc.text == "stat"  # Only the part before cursor position
    assert called_doc.cursor_position == 4  # 8 - len("git ")

def test_multi_prefix_completer_empty_input(mock_completer: MagicMock) -> None:
    """Test MultiPrefixCompleter with empty input."""
    shortcuts = {
        "git ": mock_completer
    }
    completer = MultiPrefixCompleter(shortcuts, default=None)  # type: ignore

    # Test empty input
    doc = Document("", cursor_position=0)
    completions = list(completer.get_completions(doc, None))
    assert len(completions) == 0
    mock_completer.get_completions.assert_not_called()

def test_multi_prefix_completer_multiple_matches(mock_completer: MagicMock) -> None:
    """Test MultiPrefixCompleter with multiple matching prefixes."""
    # Create a dedicated mock completer for the subcommand
    from prompt_toolkit.completion import Completer
    sub_completer = MagicMock(spec=Completer)
    sub_completion = MagicMock()
    sub_completion.text = "subcommand"
    sub_completer.get_completions.return_value = [sub_completion]

    shortcuts = {
        "git ": mock_completer,
        "git sub ": sub_completer
    }
    completer = MultiPrefixCompleter(shortcuts, default=None)  # type: ignore

    # Test with exact subcommand prefix
    doc = Document("git sub cmd", cursor_position=10)
    completions = list(completer.get_completions(doc, None))

    # Should only get completions from sub_completer
    assert len(completions) == 1
    assert completions[0].text == "subcommand"
    sub_completer.get_completions.assert_called_once()
    mock_completer.get_completions.assert_not_called()

def test_multi_prefix_completer_default_none(mock_completer: MagicMock) -> None:
    """Test MultiPrefixCompleter with default=None behavior."""
    shortcuts = {
        "git ": mock_completer
    }
    completer = MultiPrefixCompleter(shortcuts, default=None)  # type: ignore

    # Test with non-matching prefix
    doc = Document("unknown command", cursor_position=15)
    completions = list(completer.get_completions(doc, None))
    assert len(completions) == 0
    mock_completer.get_completions.assert_not_called()
