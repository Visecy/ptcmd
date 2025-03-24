import argparse
import pytest
from unittest.mock import Mock

from prompt_toolkit.document import Document
from prompt_toolkit.completion import Completion

from ptcmd.completer import ArgparseCompleter


@pytest.fixture
def simple_parser():
    """Create a simple ArgumentParser for testing."""
    parser = argparse.ArgumentParser()
    parser.add_argument('-a', '--alpha', help='Alpha option')
    parser.add_argument('-b', '--beta', help='Beta option')
    parser.add_argument('positional', help='A positional argument')
    parser.add_argument('optional_pos', nargs='?', help='An optional positional argument')
    return parser


@pytest.fixture
def completer(simple_parser):
    """Create an ArgparseCompleter instance for testing."""
    return ArgparseCompleter(simple_parser)


def test_init(simple_parser):
    """Test that the completer initializes correctly."""
    completer = ArgparseCompleter(simple_parser)
    assert completer.parser == simple_parser


def test_get_parser_options(completer, simple_parser):
    """Test that the completer extracts options correctly."""
    options = completer._get_parser_options(simple_parser)
    assert '-a' in options
    assert '--alpha' in options
    assert '-b' in options
    assert '--beta' in options
    assert '-h' in options
    assert '--help' in options
    assert len(options) == 6  # -a, --alpha, -b, --beta, -h, --help


def test_get_parser_positional_args(completer, simple_parser):
    """Test that the completer extracts positional arguments correctly."""
    positional_args = completer._get_parser_positional_args(simple_parser)
    assert 'positional' in positional_args
    assert 'optional_pos' in positional_args
    assert len(positional_args) == 2


def test_complete_option_prefix(completer):
    """Test completion of option prefixes."""
    # Create a document with a partial option
    document = Document(text="-a", cursor_position=2)
    complete_event = Mock()
    
    # Get completions
    completions = list(completer.get_completions(document, complete_event))
    
    # Should match -a and --alpha
    assert len(completions) == 1
    assert completions[0].text == '-a'
    assert completions[0].start_position == -2


def test_complete_long_option_prefix(completer):
    """Test completion of long option prefixes."""
    # Create a document with a partial long option
    document = Document(text="--a", cursor_position=3)
    complete_event = Mock()
    
    # Get completions
    completions = list(completer.get_completions(document, complete_event))
    
    # Should match --alpha
    assert len(completions) == 1
    assert completions[0].text == '--alpha'
    assert completions[0].start_position == -3


def test_complete_after_space(completer):
    """Test completion after a space."""
    # Create a document with a space at the end
    document = Document(text="command ", cursor_position=8)
    complete_event = Mock()
    
    # Get completions
    completions = list(completer.get_completions(document, complete_event))
    
    # Should suggest only options (not positional arguments)
    option_texts = [c.text for c in completions]
    assert '-a' in option_texts
    assert '--alpha' in option_texts
    assert '-b' in option_texts
    assert '--beta' in option_texts
    assert '-h' in option_texts
    assert '--help' in option_texts
    assert 'positional' not in option_texts
    assert 'optional_pos' not in option_texts
    assert len(completions) == 6  # Only options, no positional args


def test_handle_unclosed_quotes(completer):
    """Test handling of unclosed quotes."""
    # Create a document with unclosed quotes
    document = Document(text='command "unclosed', cursor_position=16)
    complete_event = Mock()
    
    # Get completions - should not raise an exception
    completions = list(completer.get_completions(document, complete_event))
    
    # Should suggest options since we're at the beginning of a new token
    assert len(completions) > 0


def test_empty_input(completer):
    """Test completion with empty input."""
    document = Document(text="", cursor_position=0)
    complete_event = Mock()
    
    completions = list(completer.get_completions(document, complete_event))
    
    # Should suggest all options
    option_texts = [c.text for c in completions]
    assert '-a' in option_texts
    assert '--alpha' in option_texts
    assert '-b' in option_texts
    assert '--beta' in option_texts
    assert '-h' in option_texts
    assert '--help' in option_texts
    assert len(completions) == 6  # Only options, no positional args for empty input