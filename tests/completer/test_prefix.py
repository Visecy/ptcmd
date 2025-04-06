from unittest.mock import Mock

import pytest
from prompt_toolkit.completion import Completer, Completion
from prompt_toolkit.document import Document

from ptcmd.completer import PrefixCompleter


@pytest.fixture
def mock_completer() -> Mock:
    """Create a mock completer for testing."""
    completer = Mock(spec=Completer)
    return completer


def test_init() -> None:
    """Test that the completer initializes correctly."""
    prefix = "git "
    mock_completer = Mock(spec=Completer)
    completer = PrefixCompleter(prefix, mock_completer)

    assert completer.prefix == prefix
    assert completer.completer == mock_completer


def test_get_completions_with_matching_prefix(mock_completer: Mock) -> None:
    """Test completions when text starts with the prefix."""
    # Setup
    prefix = "git "
    completer = PrefixCompleter(prefix, mock_completer)

    # Create a document with text that starts with the prefix
    document = Document(text="git status", cursor_position=10)
    complete_event = Mock()

    # Setup mock to return some completions
    mock_completion = Completion(
        text="status",
        start_position=-6,  # -len("status")
        display="status",
        display_meta="Show the working tree status",
    )
    mock_completer.get_completions.return_value = [mock_completion]

    # Get completions
    completions = list(completer.get_completions(document, complete_event))

    # Verify
    assert len(completions) == 1
    assert completions[0].text == "status"
    assert completions[0].start_position == -6  # Should be the same as the original
    # Note: display and display_meta are FormattedText objects, not strings

    # Verify that the mock was called with the correct document
    # The document passed to the nested completer should have the prefix removed
    mock_completer.get_completions.assert_called_once()
    called_document = mock_completer.get_completions.call_args[0][0]
    assert called_document.text == "status"
    assert called_document.cursor_position == 6  # 10 - len("git ")


def test_get_completions_with_prefix_only(mock_completer: Mock) -> None:
    """Test completions when text is exactly the prefix."""
    # Setup
    prefix = "git "
    completer = PrefixCompleter(prefix, mock_completer)

    # Create a document with text that is exactly the prefix
    document = Document(text="git ", cursor_position=4)
    complete_event = Mock()

    # Setup mock to return some completions
    mock_completion = Completion(
        text="status", start_position=0, display="status", display_meta="Show the working tree status"
    )
    mock_completer.get_completions.return_value = [mock_completion]

    # Get completions
    completions = list(completer.get_completions(document, complete_event))

    # Verify
    assert len(completions) == 1
    assert completions[0].text == "status"
    assert completions[0].start_position == 0

    # Verify that the mock was called with the correct document
    mock_completer.get_completions.assert_called_once()
    called_document = mock_completer.get_completions.call_args[0][0]
    assert called_document.text == ""
    assert called_document.cursor_position == 0


def test_get_completions_without_matching_prefix(mock_completer: Mock) -> None:
    """Test that no completions are returned when text doesn't start with the prefix."""
    # Setup
    prefix = "git "
    completer = PrefixCompleter(prefix, mock_completer)

    # Create a document with text that doesn't start with the prefix
    document = Document(text="commit ", cursor_position=7)
    complete_event = Mock()

    # Get completions
    completions = list(completer.get_completions(document, complete_event))

    # Verify
    assert len(completions) == 0

    # Verify that the mock was not called
    mock_completer.get_completions.assert_not_called()


def test_get_completions_with_cursor_in_middle(mock_completer: Mock) -> None:
    """Test completions when cursor is in the middle of the text."""
    # Setup
    prefix = "git "
    completer = PrefixCompleter(prefix, mock_completer)

    # Create a document with cursor in the middle of the text
    document = Document(text="git status --verbose", cursor_position=10)  # Cursor after "status"
    complete_event = Mock()

    # Setup mock to return some completions
    mock_completion = Completion(
        text="stat",
        start_position=-4,  # -len("stat")
        display="stat",
        display_meta="Partial status",
    )
    mock_completer.get_completions.return_value = [mock_completion]

    # Get completions
    completions = list(completer.get_completions(document, complete_event))

    # Verify
    assert len(completions) == 1
    assert completions[0].text == "stat"
    assert completions[0].start_position == -4

    # Verify that the mock was called with the correct document
    mock_completer.get_completions.assert_called_once()
    called_document = mock_completer.get_completions.call_args[0][0]
    assert called_document.text == "status"
    assert called_document.cursor_position == 6  # 10 - len("git ")


def test_get_completions_preserves_completion_attributes(mock_completer: Mock) -> None:
    """Test that all completion attributes are preserved."""
    # Setup
    prefix = "git "
    completer = PrefixCompleter(prefix, mock_completer)

    # Create a document with text that starts with the prefix
    document = Document(text="git status", cursor_position=10)
    complete_event = Mock()

    # Setup mock to return a completion with all attributes set
    mock_completion = Completion(
        text="status",
        start_position=-6,
        display="STATUS",  # Different display
        display_meta="Show status",
        style="class:special",  # Custom style
    )
    mock_completer.get_completions.return_value = [mock_completion]

    # Get completions
    completions = list(completer.get_completions(document, complete_event))

    # Verify all attributes are preserved
    assert len(completions) == 1
    assert completions[0].text == "status"
    assert completions[0].start_position == -6
    # Note: display and display_meta are FormattedText objects, not strings
    assert completions[0].style == "class:special"


def test_get_completions_empty_input(mock_completer: Mock) -> None:
    """Test completions with empty input."""
    # Setup
    prefix = "git "
    completer = PrefixCompleter(prefix, mock_completer)

    # Create empty document
    document = Document(text="", cursor_position=0)
    complete_event = Mock()

    # Get completions
    completions = list(completer.get_completions(document, complete_event))

    # Verify
    assert len(completions) == 0
    mock_completer.get_completions.assert_not_called()


def test_get_completions_partial_prefix_match(mock_completer: Mock) -> None:
    """Test completions with partial prefix match."""
    # Setup
    prefix = "git "
    completer = PrefixCompleter(prefix, mock_completer)

    # Create document with partial prefix
    document = Document(text="gi", cursor_position=2)
    complete_event = Mock()

    # Get completions
    completions = list(completer.get_completions(document, complete_event))

    # Verify
    assert len(completions) == 0
    mock_completer.get_completions.assert_not_called()


def test_get_completions_special_char_prefix(mock_completer: Mock) -> None:
    """Test completions with special character prefix."""
    # Setup
    prefix = "!cmd "
    completer = PrefixCompleter(prefix, mock_completer)

    # Create document with special prefix
    document = Document(text="!cmd list", cursor_position=9)
    complete_event = Mock()

    # Setup mock to return some completions
    mock_completion = Completion(
        text="list",
        start_position=-4,
        display="list",
        display_meta="List items",
    )
    mock_completer.get_completions.return_value = [mock_completion]

    # Get completions
    completions = list(completer.get_completions(document, complete_event))

    # Verify
    assert len(completions) == 1
    assert completions[0].text == "list"
    assert completions[0].start_position == -4

    # Verify that the mock was called with the correct document
    mock_completer.get_completions.assert_called_once()
    called_document = mock_completer.get_completions.call_args[0][0]
    assert called_document.text == "list"
    assert called_document.cursor_position == 4  # 9 - len("!cmd ")
