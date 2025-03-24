import shlex
import textwrap
from cmd import Cmd as _Cmd
from typing import IO, Any, Callable, Dict, List, Optional, Tuple, Type, cast

from prompt_toolkit import PromptSession
from prompt_toolkit.completion import WordCompleter
from prompt_toolkit.formatted_text import ANSI, HTML, FormattedText
from prompt_toolkit.patch_stdout import StdoutProxy
from rich.columns import Columns
from rich.console import Console
from rich.text import Text
from rich.panel import Panel
from rich.theme import Theme

from . import constants
from .theme import DEFAULT as DEFAULT_THEME
from .completer import ArgparseCompleter


class Cmd(_Cmd):
    prompt: Any = Text.from_markup("([cmd.prompt]Cmd[/cmd.prompt]) ")

    default_category = "Uncategorized"
    doc_leader = ""

    def __init__(
        self,
        *,
        session: Optional[PromptSession] = None,
        console: Optional[Console] = None,
        theme: Optional[Theme] = None,
    ) -> None:
        self.cmdqueue = []
        self.theme = theme or DEFAULT_THEME
        self.session = session or PromptSession()
        self.stdout = cast(IO[str], StdoutProxy(raw=True, sleep_between_writes=0.01))
        self.console = console or Console(file=self.stdout, theme=self.theme)

    def cmdloop(self, intro: Optional[Any] = None) -> None:
        self.preloop()
        try:
            if intro is not None:
                self.intro = intro
            if self.intro:
                self.console.print(self.intro)
            stop = None
            while not stop:
                if self.cmdqueue:
                    line = self.cmdqueue.pop(0)
                else:
                    prompt = self._render_rich_text(self.prompt)
                    if isinstance(prompt, str):
                        prompt = ANSI(prompt)
                    try:
                        line = self.session.prompt(
                            prompt,
                            completer=WordCompleter(self.get_visible_commands()),
                        )
                    except KeyboardInterrupt:
                        continue
                line = self.precmd(line)
                stop = self.onecmd(line)
                stop = self.postcmd(stop, line)
        finally:
            self.postloop()

    def default(self, line: str) -> None:
        self.perror(f"Unknown command: {line}")

    def do_help(self, arg):
        """List available commands or provide detailed help for a specific command"""
        if not arg:
            return self._help_menu()
        # XXX check arg syntax
        try:
            func = getattr(self, constants.HELP_FUNC_PREFIX + arg)
        except AttributeError:
            try:
                doc = getattr(self, constants.COMMAND_FUNC_PREFIX + arg).__doc__
                if doc:
                    self.poutput(textwrap.dedent(doc))
                    return
            except AttributeError:
                pass
            self.poutput(self.nohelp % (arg,))
            return
        func()

    def _help_menu(self, verbose: bool = False) -> None:
        """Show a list of commands which help can be displayed for"""
        cmds_cats, cmds_doc, cmds_undoc, help_topics = self._build_command_info()

        if not cmds_cats:
            # No categories found, fall back to standard behavior
            self.poutput(self.doc_leader)
            self.print_topics(self.doc_header, cmds_doc)
        else:
            # Categories found, Organize all commands by category
            self.poutput(self.doc_leader)
            self.poutput(self.doc_header, end="\n\n")
            for category in sorted(cmds_cats.keys()):
                self.print_topics(category, cmds_cats[category])
            self.print_topics(self.default_category, cmds_doc)

        self.print_topics(self.misc_header, help_topics)
        self.print_topics(self.undoc_header, cmds_undoc)

    def _build_command_info(self) -> Tuple[Dict[str, List[str]], List[str], List[str], List[str]]:
        # Get a sorted list of help topics
        help_topics = self.get_help_topics()
        help_topics.sort()

        # Get a sorted list of visible command names
        visible_commands = self.get_visible_commands()
        visible_commands.sort()

        cmds_doc: List[str] = []
        cmds_undoc: List[str] = []
        cmds_cats: Dict[str, List[str]] = {}
        for command in visible_commands:
            func = cast(Callable, self.cmd_func(command))
            has_help_func = has_parser = False

            if command in help_topics:
                # Prevent the command from showing as both a command and help topic in the output
                help_topics.remove(command)

                # Non-argparse commands can have help_functions for their documentation
                has_help_func = not has_parser

            if hasattr(func, constants.CMD_ATTR_HELP_CATEGORY):
                category: str = getattr(func, constants.CMD_ATTR_HELP_CATEGORY)
                cmds_cats.setdefault(category, [])
                cmds_cats[category].append(command)
            elif func.__doc__ or has_help_func or has_parser:
                cmds_doc.append(command)
            else:
                cmds_undoc.append(command)
        return cmds_cats, cmds_doc, cmds_undoc, help_topics

    def do_exit(self, line: str) -> bool:
        self.poutput("Bye!")
        return True

    def print_topics(self, header: str, cmds: Optional[List[str]], cmdlen: Optional[int] = None, maxcol: Optional[int] = None) -> None:
        if not cmds:
            return
        panel = Panel(
            Columns(cmds, width=maxcol),
            title=header,
            title_align="left"
        )
        self.poutput(panel)

    def columnize(self, list: Optional[List[str]], displaywidth: Optional[int] = None) -> None:
        if list is None:
            self.console.print("<empty>")
            return
        self.console.print(
            Columns(
                [f"[bold]{item}[/bold]" for item in list],
                width=displaywidth,
            )
        )

    def cmd_func(self, command: str) -> Optional[Callable]:
        """
        Get the function for a command

        :param command: the name of the command

        Example:

        ```py
        helpfunc = self.cmd_func('help')
        ```

        helpfunc now contains a reference to the ``do_help`` method
        """
        func_name = constants.COMMAND_FUNC_PREFIX + command
        func = getattr(self, func_name, None)
        return func if callable(func) else None

    def get_all_commands(self) -> List[str]:
        """Return a list of all commands"""
        return [
            name[len(constants.COMMAND_FUNC_PREFIX) :]
            for name in self.get_names()
            if name.startswith(constants.COMMAND_FUNC_PREFIX) and callable(getattr(self, name))
        ]

    def get_visible_commands(self) -> List[str]:
        """Return a list of commands that have not been hidden or disabled"""
        return [
            command
            for command in self.get_all_commands()
            if not getattr(command, constants.CMD_ATTR_HIDDEN, None)
            and not getattr(command, constants.CMD_ATTR_DISABLED, None)
        ]

    def get_help_topics(self) -> List[str]:
        """Return a list of help topics"""
        all_topics = [
            name[len(constants.HELP_FUNC_PREFIX) :]
            for name in self.get_names()
            if name.startswith(constants.HELP_FUNC_PREFIX) and callable(getattr(self, name))
        ]

        # Filter out hidden and disabled commands
        return [
            topic
            for topic in all_topics
            if not getattr(topic, constants.CMD_ATTR_HIDDEN, False) and not getattr(topic, constants.CMD_ATTR_DISABLED, False)
        ]

    @property
    def visible_prompt(self) -> str:
        """Read-only property to get the visible prompt with any ANSI style escape codes stripped.

        Used by transcript testing to make it easier and more reliable when users are doing things like coloring the
        prompt using ANSI color codes.

        :return: prompt stripped of any ANSI escape codes
        """
        return str(self.prompt)

    def poutput(self, *objs, sep: str = " ", end: str = "\n") -> None:
        self.console.print(*objs, sep=sep, end=end)

    def perror(self, *objs, sep: str = " ", end: str = "\n") -> None:
        self.console.log(*objs, sep=sep, end=end, style="cmd.error", _stack_offset=2)

    def psuccess(self, *objs, sep: str = " ", end: str = "\n") -> None:
        self.console.print(*objs, sep=sep, end=end, style="cmd.success")

    def pwarning(self, *objs, sep: str = " ", end: str = "\n") -> None:
        self.console.log(*objs, sep=sep, end=end, style="cmd.warning", _stack_offset=2)

    def pexcept(self, *, show_locals: bool = False) -> None:
        self.console.print_exception(show_locals=show_locals)
    
    def _render_rich_text(self, text: Any) -> Any:
        if isinstance(text, (str, list, FormattedText, ANSI, HTML)):
            return text
        with self.console.capture() as capture:
            self.console.print(text, end="")
        return capture.get()
