from rich.theme import Theme

DEFAULT_STYLE = {
    "cmd.success": "green",
    "cmd.warning": "yellow",
    "cmd.error": "red bold",
    "cmd.prompt": "cyan bold underline"
}

DEFAULT = Theme(DEFAULT_STYLE)
