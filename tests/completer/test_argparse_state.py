import argparse

from ptcmd.completer import ArgparseCompleter

def test_argument_state_nargs_fixed() -> None:
    """Test _ArgumentState with fixed number nargs."""
    parser = argparse.ArgumentParser()
    action = parser.add_argument("--fixed", nargs=2)
    state = ArgparseCompleter._ArgumentState(action)
    assert state.min == 2
    assert state.max == 2
    assert not state.is_remainder

def test_argument_state_nargs_none() -> None:
    """Test _ArgumentState with nargs=None."""
    parser = argparse.ArgumentParser()
    action = parser.add_argument("--none")
    state = ArgparseCompleter._ArgumentState(action)
    assert state.min == 1
    assert state.max == 1
    assert not state.is_remainder

def test_argument_state_nargs_optional() -> None:
    """Test _ArgumentState with nargs=OPTIONAL."""
    parser = argparse.ArgumentParser()
    action = parser.add_argument("--opt", nargs=argparse.OPTIONAL)
    state = ArgparseCompleter._ArgumentState(action)
    assert state.min == 0
    assert state.max == 1
    assert not state.is_remainder

def test_argument_state_nargs_zero_or_more() -> None:
    """Test _ArgumentState with nargs=ZERO_OR_MORE."""
    parser = argparse.ArgumentParser()
    action = parser.add_argument("--zero", nargs=argparse.ZERO_OR_MORE)
    state = ArgparseCompleter._ArgumentState(action)
    assert state.min == 0
    assert state.max == float("inf")
    assert not state.is_remainder

def test_argument_state_nargs_one_or_more() -> None:
    """Test _ArgumentState with nargs=ONE_OR_MORE."""
    parser = argparse.ArgumentParser()
    action = parser.add_argument("--one", nargs=argparse.ONE_OR_MORE)
    state = ArgparseCompleter._ArgumentState(action)
    assert state.min == 1
    assert state.max == float("inf")
    assert not state.is_remainder

def test_argument_state_nargs_remainder() -> None:
    """Test _ArgumentState with nargs=REMAINDER."""
    parser = argparse.ArgumentParser()
    action = parser.add_argument("--remainder", nargs=argparse.REMAINDER)
    state = ArgparseCompleter._ArgumentState(action)
    assert state.min == 0
    assert state.max == float("inf")
    assert state.is_remainder

def test_argument_state_nargs_range() -> None:
    """Test _ArgumentState with get_nargs_range method."""
    parser = argparse.ArgumentParser()
    action = parser.add_argument("--range")
    # Mock get_nargs_range to return (1, 2)
    action.get_nargs_range = lambda: (1, 2)  # type: ignore
    state = ArgparseCompleter._ArgumentState(action)
    assert state.min == 1
    assert state.max == 2

def test_argument_state_nargs_fixed_number() -> None:
    """Test _ArgumentState with fixed number nargs."""
    parser = argparse.ArgumentParser()
    action = parser.add_argument("--fixed", nargs=3)
    state = ArgparseCompleter._ArgumentState(action)
    assert state.min == 3
    assert state.max == 3
    assert not state.is_remainder

def test_looks_like_flag_edge_cases() -> None:
    """Test _looks_like_flag with edge cases."""
    parser = argparse.ArgumentParser()
    completer = ArgparseCompleter(parser)

    # Empty string
    assert not completer._looks_like_flag("")

    # Single character that's not a prefix
    assert not completer._looks_like_flag("a")

    # Space in token
    assert not completer._looks_like_flag("--opt value")

def test_single_prefix_char_edge_cases() -> None:
    """Test _single_prefix_char with edge cases."""
    parser = argparse.ArgumentParser()
    completer = ArgparseCompleter(parser)

    # Empty string
    assert not completer._single_prefix_char("")

    # Multiple characters
    assert not completer._single_prefix_char("--")

    # Non-prefix character
    parser = argparse.ArgumentParser(prefix_chars="+")
    completer = ArgparseCompleter(parser)
    assert not completer._single_prefix_char("-")

def test_consume_argument_edge_cases() -> None:
    """Test _consume_argument with edge cases."""
    parser = argparse.ArgumentParser()
    action = parser.add_argument("--arg", nargs=2)
    completer = ArgparseCompleter(parser)
    state = ArgparseCompleter._ArgumentState(action)
    consumed = {}

    # First consumption
    completer._consume_argument(state, "value1", consumed)
    assert state.count == 1
    assert consumed["arg"] == ["value1"]

    # Second consumption
    completer._consume_argument(state, "value2", consumed)
    assert state.count == 2
    assert consumed["arg"] == ["value1", "value2"]

def test_get_completion_texts_error_paths() -> None:
    """Test _get_completion_texts error handling paths."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--req", nargs=1, required=True)
    completer = ArgparseCompleter(parser)

    # Test with invalid input that would cause shlex to fail
    completions = list(completer._get_completion_texts(
        "'unclosed", "--req 'unclosed", 7, 14, ["--req", "'unclosed"], -7
    ))
    assert len(completions) == 0

def test_get_flag_completions_edge_cases() -> None:
    """Test _get_flag_completions with edge cases."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--flag", help="A flag")
    completer = ArgparseCompleter(parser)

    # Test with empty text
    completions = list(completer._get_flag_completions("", [], 0))
    assert len(completions) == 3  # Includes -h, --help and --flag
    assert any(c.text == "--flag" for c in completions)

def test_get_arg_completions_edge_cases() -> None:
    """Test _get_arg_completions with edge cases."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--choice", choices=["a", "b", "c"])
    completer = ArgparseCompleter(parser)
    action = parser._actions[-1]
    state = ArgparseCompleter._ArgumentState(action)

    # Test with empty text
    completions = list(completer._get_arg_completions("", state, {}, 0))
    assert len(completions) == 3
    assert all(c.text in ["a", "b", "c"] for c in completions)
