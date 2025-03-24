import argparse
import re
import shlex
from typing import Dict, List, Optional, Tuple, Any, Callable, Iterable, Set

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
    
    def __init__(self, prefix: str, completer: Completer):
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
        text = document.text_before_cursor
        
        # Check if the text starts with the prefix
        if text.startswith(self.prefix):
            # Create a new document with the text after the prefix
            prefix_length = len(self.prefix)
            remaining_text = text[prefix_length:]
            cursor_position = document.cursor_position - prefix_length
            
            # Create a new document with the remaining text
            new_document = Document(remaining_text, cursor_position)
            
            # Get completions from the nested completer
            for completion in self.completer.get_completions(new_document, complete_event):
                # Adjust the start position to account for the prefix
                yield Completion(
                    completion.text,
                    start_position=completion.start_position,
                    display=completion.display,
                    display_meta=completion.display_meta,
                    style=completion.style
                )


class ArgparseCompleter(Completer):
    """
    Completer for argparse-based commands.

    :param parser: The ArgumentParser object for the command
    :type parser: argparse.ArgumentParser

    This completer provides completion for a single command that uses argparse for argument parsing.
    It can complete options and option values based on the ArgumentParser object provided.
    """
    
    def __init__(self, parser: argparse.ArgumentParser):
        """
        Initialize the completer with a single ArgumentParser.

        :param parser: The ArgumentParser object for the command
        :type parser: argparse.ArgumentParser
        """
        self.parser = parser
    
    def get_completions(self, document: Document, complete_event: Any) -> Iterable[Completion]:
        text = document.text_before_cursor
        
        # Split the input text into tokens
        try:
            tokens = shlex.split(text)
        except ValueError:
            # Handle unclosed quotes
            # Just use a simple split and consider the command part
            tokens = text.split()
            
            # Force the behavior as if we're at a space after the command
            # This ensures we offer completions even with unclosed quotes
            text = text + ' '
        
        # Get all the options from the parser
        options = self._get_parser_options(self.parser)
        
        # If we're at the end of the text and it's not a space, complete the current token
        current_token = ''
        if not text.endswith(' ') and tokens:
            current_token = tokens[-1]
        
        # Check if we're completing an option
        if current_token.startswith('-'):
            for option in options:
                if option.startswith(current_token):
                    yield Completion(
                        option, 
                        start_position=-len(current_token),
                        display=option
                    )
        # Otherwise, suggest available options only (not positional arguments)
        elif text.endswith(' ') or not tokens:
            for option in options:
                yield Completion(option, start_position=0, display=option)
    
    def _get_parser_options(self, parser: argparse.ArgumentParser) -> List[str]:
        """
        Extract all options from an ArgumentParser object.

        :param parser: The ArgumentParser to extract options from
        :type parser: argparse.ArgumentParser
        :return: A list of option strings
        :rtype: List[str]
        """
        options = []
        
        # Extract options from the parser's actions
        for action in parser._actions:
            options.extend(action.option_strings)
        
        return sorted(options)
    
    def _get_parser_positional_args(self, parser: argparse.ArgumentParser) -> List[str]:
        """
        Extract all positional arguments from an ArgumentParser object.

        :param parser: The ArgumentParser to extract positional arguments from
        :type parser: argparse.ArgumentParser
        :return: A list of positional argument names
        :rtype: List[str]
        """
        positional_args = []
        
        # Extract positional arguments from the parser's actions
        for action in parser._actions:
            # Positional arguments have empty option_strings
            if not action.option_strings and action.dest != 'help':
                positional_args.append(action.dest)
        
        return sorted(positional_args)
        