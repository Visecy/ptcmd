import argparse
import shlex
from collections import deque
from typing import Any, Dict, Generator, Iterable, List, Optional, Union

from prompt_toolkit.completion import Completer, Completion
from prompt_toolkit.document import Document


class PrefixCompleter(Completer):
    """
    Completer that applies a nested completer after a specific prefix.

    :param prefix: The string prefix that triggers the nested completer
    :param completer: The completer to use for text after the prefix

    This completer checks if the input text starts with a specified prefix,
    and if so, delegates completion to the provided completer for the text after the prefix.
    The prefix and the subsequent content don't need to be separated by a space.
    """

    def __init__(self, prefix: str, completer: Completer) -> None:
        """
        Initialize the completer with a prefix and a nested completer.

        :param prefix: The string prefix that triggers the nested completer
        :type prefix: str
        :param completer: The completer to use for text after the prefix
        :type completer: Completer
        """
        self.prefix = prefix
        self.completer = completer

    def get_completions(self, document: Document, complete_event: Any) -> Iterable[Completion]:
        text = document.text_before_cursor.lstrip()

        # Check if the text starts with the prefix
        if text.startswith(self.prefix):
            # Create a new document with the text after the prefix
            prefix_length = len(self.prefix)
            remaining_text = text[prefix_length:]
            cursor_position = document.cursor_position - prefix_length

            # Create a new document with the remaining text
            new_document = Document(remaining_text, cursor_position)

            # Get completions from the completer
            yield from self.completer.get_completions(new_document, complete_event)


class MultiPrefixCompleter(Completer):
    def __init__(self, shortcuts: Dict[str, Optional[Completer]], default: Optional[Completer] = None) -> None:
        self.shortcuts = shortcuts
        self.default = default

    def get_completions(self, document: Document, complete_event: Any) -> Generator[Completion, None, None]:
        text = document.text_before_cursor.lstrip()
        # Find the longest matching prefix
        best_match = None
        best_length = -1
        for prefix, completer in self.shortcuts.items():
            if text.startswith(prefix) and len(prefix) > best_length:
                best_match = (prefix, completer)
                best_length = len(prefix)

        if best_match is not None:
            prefix, completer = best_match
            if completer is None:
                return
            # Create a new document with the text after the prefix
            prefix_length = len(prefix)
            remaining_text = text[prefix_length:]
            cursor_position = document.cursor_position - prefix_length

            # Create a new document with the remaining text
            new_document = Document(remaining_text, cursor_position)
            yield from completer.get_completions(new_document, complete_event)
        else:
            if self.default is not None:
                yield from self.default.get_completions(document, complete_event)


class ArgparseCompleter(Completer):
    """
    Completer for argparse-based commands with advanced completion features.

    This completer provides sophisticated completion for commands using argparse,
    including subcommands, argument values, choices, and more.
    """

    def __init__(self, parser: argparse.ArgumentParser) -> None:
        """
        Create an Argparse completer for prompt_toolkit.

        :param parser: ArgumentParser instance
        :type parser: argparse.ArgumentParser
        """
        self._parser = parser
        self._flags: List[str] = []  # all flags in this command
        self._flag_to_action: Dict[str, argparse.Action] = {}  # maps flags to the argparse action object
        self._positional_actions: List[argparse.Action] = []  # actions for positional arguments
        self._subcommand_action = None  # set if parser has subcommands

        # Parse argparse actions
        for action in self._parser._actions:
            if action.option_strings:  # flag-based arguments
                for option in action.option_strings:
                    self._flags.append(option)
                    self._flag_to_action[option] = action
            else:  # positional arguments
                self._positional_actions.append(action)
                if isinstance(action, argparse._SubParsersAction):
                    self._subcommand_action = action

    def get_completions(self, document: Document, complete_event: Any) -> Generator[Completion, None, None]:
        """Generate completions as a generator for prompt_toolkit."""
        text = document.text_before_cursor
        line = document.text
        cursor_position = document.cursor_position_col

        # Tokenize using shlex
        for quote in ("", '"', "'"):
            # Handle incomplete quoting
            try:
                tokens = shlex.split(text + quote, comments=False, posix=False)
            except ValueError:
                continue
            else:
                break
        else:  # pragma: no cover
            # Revert to whitespace tokenization when shlex fails
            tokens = text.split()

        # Check if cursor is at end of text with trailing space
        ends_with_space = text.endswith(" ")

        # If ends with space, we're completing a new token
        if ends_with_space:
            tokens.append("")

        # Get the text to complete (last token)
        text_to_complete = tokens[-1] if tokens else ""

        # Calculate start position for completions
        start_position = -len(text_to_complete)

        # Yield completions directly from _get_completion_texts
        yield from self._get_completion_texts(
            text_to_complete, line, cursor_position - len(text_to_complete), cursor_position, tokens, start_position
        )

    def _get_completion_texts(
        self, text: str, line: str, begidx: int, endidx: int, tokens: List[str], start_position: int
    ) -> Generator[Completion, None, None]:
        """Generate completions by analyzing the command line state.

        :param text: The text being completed (last token)
        :type text: str
        :param line: The full command line text
        :type line: str
        :param begidx: Beginning index of text in line
        :type begidx: int
        :param endidx: Ending index of text in line
        :type endidx: int
        :param tokens: List of parsed command tokens
        :type tokens: List[str]
        :param start_position: Start position for completions
        :type start_position: int
        :return: Generator yielding Completion objects
        :rtype: Generator[Completion, None, None]
        """
        remaining_positionals = deque(self._positional_actions)
        skip_remaining_flags = False
        pos_arg_state = None
        flag_arg_state = None
        matched_flags = []
        consumed_arg_values: Dict[str, List[str]] = {}
        # Parse all but last token
        for token_index, token in enumerate(tokens[:-1]):
            if pos_arg_state and pos_arg_state.is_remainder:
                self._consume_argument(pos_arg_state, token, consumed_arg_values)
                continue

            if flag_arg_state and flag_arg_state.is_remainder:
                if token == "--":
                    flag_arg_state = None
                else:
                    self._consume_argument(flag_arg_state, token, consumed_arg_values)
                continue

            elif token == "--" and not skip_remaining_flags:
                if flag_arg_state and isinstance(flag_arg_state.min, int) and flag_arg_state.count < flag_arg_state.min:
                    return
                flag_arg_state = None
                skip_remaining_flags = True
                continue

            if self._looks_like_flag(token) and not skip_remaining_flags:
                if flag_arg_state and isinstance(flag_arg_state.min, int) and flag_arg_state.count < flag_arg_state.min:
                    return

                flag_arg_state = None
                action = None

                if token in self._flag_to_action:
                    action = self._flag_to_action[token]
                elif self._parser.allow_abbrev:
                    candidates = [f for f in self._flag_to_action if f.startswith(token)]
                    if len(candidates) == 1:
                        action = self._flag_to_action[candidates[0]]

                if action:
                    if not isinstance(action, (argparse._AppendAction, argparse._AppendConstAction, argparse._CountAction)):
                        matched_flags.extend(action.option_strings)
                        consumed_arg_values[action.dest] = []

                    new_arg_state = self._ArgumentState(action)
                    if new_arg_state.max > 0:  # type: ignore[operator]
                        flag_arg_state = new_arg_state
                        skip_remaining_flags = flag_arg_state.is_remainder

            elif flag_arg_state:
                self._consume_argument(flag_arg_state, token, consumed_arg_values)
                if isinstance(flag_arg_state.max, (float, int)) and flag_arg_state.count >= flag_arg_state.max:
                    flag_arg_state = None

            else:
                if pos_arg_state is None and remaining_positionals:
                    action = remaining_positionals.popleft()
                    if action == self._subcommand_action:
                        assert self._subcommand_action is not None
                        if token in self._subcommand_action.choices:
                            parser = self._subcommand_action.choices[token]
                            completer = ArgparseCompleter(parser)
                            yield from completer._get_completion_texts(
                                text, line, begidx, endidx, tokens[token_index + 1 :], start_position
                            )
                        return
                    else:
                        pos_arg_state = self._ArgumentState(action)

                if pos_arg_state:
                    self._consume_argument(pos_arg_state, token, consumed_arg_values)
                    if pos_arg_state.is_remainder:
                        skip_remaining_flags = True
                    elif isinstance(pos_arg_state.max, (float, int)) and pos_arg_state.count >= pos_arg_state.max:
                        pos_arg_state = None
                        if remaining_positionals and remaining_positionals[0].nargs == argparse.REMAINDER:
                            skip_remaining_flags = True

        # Complete last token
        if self._looks_like_flag(text) and not skip_remaining_flags:
            if flag_arg_state and isinstance(flag_arg_state.min, int) and flag_arg_state.count < flag_arg_state.min:
                return
            yield from self._get_flag_completions(text, matched_flags, start_position)
            return

        if flag_arg_state:
            yield from self._get_arg_completions(text, flag_arg_state, consumed_arg_values, start_position)
            return

        elif pos_arg_state or remaining_positionals:
            if pos_arg_state is None and remaining_positionals:
                action = remaining_positionals.popleft()
                pos_arg_state = self._ArgumentState(action)
            if pos_arg_state:
                yield from self._get_arg_completions(text, pos_arg_state, consumed_arg_values, start_position)
            return

        if not skip_remaining_flags and (self._single_prefix_char(text) or not remaining_positionals):
            yield from self._get_flag_completions(text, matched_flags, start_position)

    def _get_flag_completions(
        self, text: str, matched_flags: List[str], start_position: int
    ) -> Generator[Completion, None, None]:
        """Yield unused flags that match the text."""
        for flag in self._flags:
            if flag in matched_flags:
                continue
            action = self._flag_to_action[flag]
            if action.help != argparse.SUPPRESS and flag.startswith(text):
                yield Completion(
                    text=flag, start_position=start_position, display=flag, display_meta=action.help if action.help else None
                )

    def _get_arg_completions(
        self,
        text: str,
        arg_state: "_ArgumentState",
        consumed_arg_values: Dict[str, List[str]],
        start_position: int,
    ) -> Generator[Completion, None, None]:
        """Yield argument value completions."""
        if arg_state.action.choices is None:
            return
        used_values = consumed_arg_values.get(arg_state.action.dest, [])
        for choice in arg_state.action.choices:
            choice_str = str(choice)
            if not choice_str.startswith(text) or choice_str in used_values:
                continue
            yield Completion(
                text=choice_str,
                start_position=start_position,
                display=choice_str,
                display_meta=(
                    f"{arg_state.action.metavar} - {arg_state.action.help}"
                    if arg_state.action.help
                    else f"{arg_state.action.metavar}"
                ),
            )

    def _looks_like_flag(self, token: str) -> bool:
        """Check if token looks like a flag."""
        if len(token) < 1:
            return False
        if token[0] not in self._parser.prefix_chars:
            return False
        if hasattr(self._parser, "_negative_number_matcher"):
            if self._parser._negative_number_matcher.match(token):
                if not getattr(self._parser, "_has_negative_number_optionals", False):
                    return False
        if " " in token:
            return False
        return True

    def _single_prefix_char(self, token: str) -> bool:
        """Check if token is just a single flag prefix char."""
        return len(token) == 1 and token[0] in self._parser.prefix_chars

    def _consume_argument(self, arg_state: "_ArgumentState", token: str, consumed_arg_values: Dict[str, List[str]]) -> None:
        """Record consumption of an argument value."""
        arg_state.count += 1
        consumed_arg_values.setdefault(arg_state.action.dest, [])
        consumed_arg_values[arg_state.action.dest].append(token)

    class _ArgumentState:
        """Track state of an argument being parsed.

        This helper class tracks how many values have been consumed for an argument
        and whether it's a remainder-type argument that consumes all remaining input.

        :ivar action: The argparse Action being tracked
        :vartype action: argparse.Action
        :ivar min: Minimum number of values required
        :vartype min: Union[int, str]
        :ivar max: Maximum number of values allowed
        :vartype max: Union[float, int, str]
        :ivar count: Number of values consumed so far
        :vartype count: int
        :ivar is_remainder: Whether this is a remainder argument
        :vartype is_remainder: bool
        """

        def __init__(self, arg_action: argparse.Action) -> None:
            self.action = arg_action
            self.min: Union[int, str]
            self.max: Union[float, int, str]
            self.count = 0
            self.is_remainder = self.action.nargs == argparse.REMAINDER

            nargs_range = getattr(self.action, "get_nargs_range", lambda: None)()  # pragma: no cover
            if nargs_range is not None:  # pragma: no cover
                self.min, self.max = nargs_range
            elif self.action.nargs is None:
                self.min, self.max = 1, 1
            elif self.action.nargs == argparse.OPTIONAL:
                self.min, self.max = 0, 1
            elif self.action.nargs in (argparse.ZERO_OR_MORE, argparse.REMAINDER):
                self.min, self.max = 0, float("inf")
            elif self.action.nargs == argparse.ONE_OR_MORE:
                self.min, self.max = 1, float("inf")
            else:
                self.min = self.max = self.action.nargs
