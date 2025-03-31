"""Theme configuration for ptcmd's rich console output.

This module defines the default color styles used for different types of
command output (success, warning, error) and the prompt.
"""

from rich.theme import Theme


DEFAULT_STYLE = {
    "cmd.success": "green",
    "cmd.warning": "yellow",
    "cmd.error": "red bold",
    "cmd.prompt": "cyan bold underline",
    "cmd.help.name": "white bold not dim",
    "cmd.help.doc": "dim bright_cyan",
    "cmd.help.misc": "dim cyan",
    "cmd.help.undoc": "dim blue",
}

DEFAULT = Theme(DEFAULT_STYLE)
