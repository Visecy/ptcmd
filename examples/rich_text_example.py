import sys
import os

from rich.__main__ import make_test_card
from rich.columns import Columns
from rich.highlighter import ReprHighlighter
from rich.table import Table

from ptcmd import Arg, Cmd, auto_argument


class RichTextApp(Cmd):
    DEFAULT_PROMPT = "[cmd.prompt]rich[/cmd.prompt]> "

    @auto_argument
    def do_test_card(self) -> None:
        """show rich text"""
        self.poutput(make_test_card())

    @auto_argument
    def do_pager(self, *, styles: Arg[bool, "-s", "--styles", {"help": ""}] = False) -> None:  # noqa: F821,B002
        """show rich text with pager"""
        with self.console.pager(styles=styles):
            self.poutput(make_test_card())

    @auto_argument
    def do_columns(self) -> None:
        """show rich text with columns"""
        console = self.console
        files = [f"{i} {s}" for i, s in enumerate(sorted(os.listdir()))]
        columns = Columns(files, padding=(0, 1), expand=False, equal=False)
        console.print(columns)
        console.rule()
        columns.column_first = True
        console.print(columns)
        columns.right_to_left = True
        console.rule()
        console.print(columns)
    
    @auto_argument
    def do_table(self) -> None:
        """show rich text with table"""
        console = self.console
        table = Table(
            title="Star Wars Movies",
            caption="Rich example table",
            caption_justify="right",
        )

        table.add_column(
            "Released", header_style="bright_cyan", style="cyan", no_wrap=True
        )
        table.add_column("Title", style="magenta")
        table.add_column("Box Office", justify="right", style="green")

        table.add_row(
            "Dec 20, 2019",
            "Star Wars: The Rise of Skywalker",
            "$952,110,690",
        )
        table.add_row("May 25, 2018", "Solo: A Star Wars Story", "$393,151,347")
        table.add_row(
            "Dec 15, 2017",
            "Star Wars Ep. V111: The Last Jedi",
            "$1,332,539,889",
            style="on black",
            end_section=True,
        )
        table.add_row(
            "Dec 16, 2016",
            "Rogue One: A Star Wars Story",
            "$1,332,439,889",
        )

        def header(text: str) -> None:
            console.print()
            console.rule(highlight(text))
            console.print()

        highlight = ReprHighlighter()
        header("Example Table")
        console.print(table, justify="center")

        table.expand = True
        header("expand=True")
        console.print(table)

        table.width = 50
        header("width=50")

        console.print(table, justify="center")

        table.width = None
        table.expand = False
        table.row_styles = ["dim", "none"]
        header("row_styles=['dim', 'none']")

        console.print(table, justify="center")

        table.width = None
        table.expand = False
        table.row_styles = ["dim", "none"]
        table.leading = 1
        header("leading=1, row_styles=['dim', 'none']")
        console.print(table, justify="center")

        table.width = None
        table.expand = False
        table.row_styles = ["dim", "none"]
        table.show_lines = True
        table.leading = 0
        header("show_lines=True, row_styles=['dim', 'none']")
        console.print(table, justify="center")


if __name__ == "__main__":
    sys.exit(RichTextApp().cmdloop())
