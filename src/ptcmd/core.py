import asyncio
import pydoc
import shlex
import sys
from asyncio import iscoroutine
from collections import defaultdict
from typing import (Any, Callable, ClassVar, Coroutine, Dict, List, Optional,
                    Sequence, Set, TextIO, Tuple, TypeVar, Union, cast)

from prompt_toolkit.application import create_app_session
from prompt_toolkit.completion import Completer, NestedCompleter, merge_completers
from prompt_toolkit.formatted_text import ANSI, is_formatted_text
from prompt_toolkit.input import create_input
from prompt_toolkit.lexers import PygmentsLexer
from prompt_toolkit.output import DummyOutput, create_output
from prompt_toolkit.patch_stdout import StdoutProxy
from prompt_toolkit.shortcuts.prompt import CompleteStyle, PromptSession
from pygments.lexers.shell import BashLexer
from rich.columns import Columns
from rich.console import Console
from rich.layout import Layout
from rich.panel import Panel
from rich.style import Style
from rich.theme import Theme

from . import constants
from .argument import Arg
from .decorators import auto_argument
from .completer import PrefixCompleter
from .info import CommandInfo, CommandInfoGetter, build_cmd_info
from .theme import DEFAULT as DEFAULT_THEME


_T = TypeVar("_T")
CommandFunc = Union[CommandInfoGetter, Callable[["BaseCmd", List[str]], Optional[bool]]]


async def _ensure_coroutine(coro: Union[Coroutine[Any, Any, _T], _T]) -> _T:
    """Ensure the input is awaited if it's a coroutine, otherwise return as-is.
    
    :param coro: Either a coroutine or a regular value
    :type coro: Union[Coroutine[Any, Any, _T], _T]
    :return: The result of the coroutine or the value itself
    :rtype: _T
    """
    if iscoroutine(coro):
        return await coro
    else:
        return coro


class BaseCmd(object):
    """Base class for command line interface.

    This class provides the foundation for building command-line interfaces.
    It implements core functionality for command registration and execution.
    """

    __slots__ = [
        "stdin",
        "stdout",
        "raw_stdout",
        "theme",
        "prompt",
        "shortcuts",
        "intro",
        "doc_leader",
        "doc_header",
        "misc_header",
        "undoc_header",
        "nohelp",
        "cmdqueue",
        "session",
        "console",
        "lastcmd",
        "command_info",
        "default_category",
    ]
    __commands__: ClassVar[Set[CommandFunc]] = set()

    DEFAULT_PROMPT: ClassVar[Any] = "([cmd.prompt]Cmd[/cmd.prompt]) "
    DEFAULT_SHORTCUTS: ClassVar[Dict[str, str]] = {'?': 'help', '!': 'shell', '@': 'run_script'}

    def __init__(
        self,
        stdin: Optional[TextIO] = None,
        stdout: Optional[TextIO] = None,
        *,
        session: Optional[Union[PromptSession, Callable[..., PromptSession]]] = None,
        console: Optional[Console] = None,
        theme: Optional[Theme] = None,
        prompt: Any = None,
        shortcuts: Optional[Dict[str, str]] = None,
        intro: Optional[Any] = None,
        doc_leader="",
        doc_header="Documented commands (type help <topic>):",
        misc_header="Miscellaneous help topics:",
        undoc_header="Undocumented commands:",
        nohelp="No help on %s",
    ) -> None:
        if stdin is not None:
            self.stdin = stdin
        else:
            self.stdin = sys.stdin
        if stdout is not None:
            self.raw_stdout = stdout
        else:
            self.raw_stdout = sys.stdout
        
        self.theme = theme or DEFAULT_THEME
        self.prompt = prompt or self.DEFAULT_PROMPT
        self.shortcuts = shortcuts or self.DEFAULT_SHORTCUTS
        self.intro = intro
        self.doc_leader = doc_leader
        self.doc_header = doc_header
        self.misc_header = misc_header
        self.undoc_header = undoc_header
        self.nohelp = nohelp
        # If any command has been categorized, then all other commands that haven't been categorized
        # will display under this section in the help output.
        self.default_category = 'Uncategorized'

        input = create_input(self.stdin)
        if self.stdin.isatty():
            output = create_output(self.raw_stdout)
            with create_app_session(input, output):
                self.stdout = cast(TextIO, StdoutProxy(raw=True, sleep_between_writes=0.01))
        else:
            output = DummyOutput()
            self.stdout = self.raw_stdout
        if callable(session):
            self.session = session(input, output)
        else:
            self.session = session or PromptSession(input=input, output=output)
        self.console = console or Console(file=self.stdout, theme=self.theme)

        self.cmdqueue = []
        self.lastcmd = ''
        self.command_info = {
            info.name: info
            for info in map(self._build_command_info, self.__commands__)
        }

    def cmdloop(self, intro: Optional[Any] = None) -> None:
        return asyncio.run(self.cmdloop_async(intro))

    async def cmdloop_async(self, intro: Optional[Any] = None) -> None:
        await _ensure_coroutine(self.preloop())
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
                        line = await self.session.prompt_async(
                            prompt,
                            completer=self.completer,
                            lexer=PygmentsLexer(BashLexer),
                            complete_in_thread=True,
                            complete_style=CompleteStyle.READLINE_LIKE
                        )
                    except KeyboardInterrupt:
                        continue
                    except EOFError:
                        line = "EOF"
                line = await _ensure_coroutine(self.precmd(line))
                stop = await self.onecmd(line)
                stop = await _ensure_coroutine(self.postcmd(stop, line))
        finally:
            await _ensure_coroutine(self.postloop())

    def precmd(self, line: str) -> str:
        """Hook method executed just before command line interpretation.

        Called after the input prompt is generated and issued, but before
        the command line is interpreted.

        :param line: The input command line
        :type line: str
        :return: The processed command line
        :rtype: str
        """
        return line

    def postcmd(self, stop: Any, line: str) -> Any:
        """Hook method executed after command dispatch is finished.

        :param stop: Flag indicating whether to stop command loop
        :type stop: Any
        :param line: The input command line that was executed
        :type line: str
        :return: Flag indicating whether to stop command loop
        :rtype: Any
        """
        return stop

    def preloop(self) -> None:
        """Hook method executed once at the start of command processing.

        Called once when cmdloop() is called, before any commands are processed.

        This is typically used for initialization tasks that need to happen
        before command processing begins.
        """
        pass

    def postloop(self) -> None:
        """Hook method executed once at the end of command processing.

        Called once when cmdloop() is about to return, after all commands
        have been processed.

        This is typically used for cleanup tasks that need to happen
        after command processing completes.
        """
        pass

    def parseline(self, line: str) -> Union[Tuple[str, List[str], str], Tuple[None, None, str]]:
        """Parse the input line into command name and arguments.
        
        Handles command shortcuts and normal command parsing.
        
        :param line: The input command line to parse
        :type line: str
        :return: Tuple containing:
            - command name (or None if invalid/empty)
            - command arguments (or None if no args)
            - original line (stripped)
        :rtype: Tuple[Optional[str], Optional[List[str]], str]
        """
        line = line.strip()
        if not line:
            return None, None, line
        for shortcut, cmd_name in self.shortcuts.items():
            if line.startswith(shortcut):
                if cmd_name not in self.command_info:
                    return None, None, line
                line = f"{cmd_name} {line[len(shortcut):]}"
        tokens = shlex.split(line, comments=False, posix=False)
        return tokens[0], tokens[1:], line

    async def onecmd(self, line: str) -> Optional[bool]:
        """Execute a single command line.
        
        :param line: The input command line to execute
        :type line: str
        :return: Boolean to stop command loop (True) or continue (False/None)
        :rtype: Optional[bool]
        """
        cmd, arg, _line = await _ensure_coroutine(self.parseline(line))
        if not _line:
            return await _ensure_coroutine(self.emptyline())
        if not cmd:
            return await _ensure_coroutine(self.default(_line))
        if line != "EOF":
            self.lastcmd = line

        info = self.command_info.get(cmd)
        if info is None or info.disabled:
            return await _ensure_coroutine(self.default(line))
        assert arg is not None
        result = await _ensure_coroutine(info.cmd_func(arg))
        return bool(result) if result is not None else None

    async def emptyline(self) -> Optional[bool]:
        """Handle empty line input.

        Called when an empty line is entered in response to the prompt.
        By default, repeats the last nonempty command entered.

        :return: Boolean to stop command loop (True) or continue (False/None)
        :rtype: Optional[bool]
        """
        if self.lastcmd:
            return await self.onecmd(self.lastcmd)

    async def default(self, line: str) -> Optional[bool]:
        """Handle unknown commands.

        Called when an unknown command is entered. By default, displays
        an error message indicating the command is unknown.

        :param line: The unknown command line that was entered
        :type line: str
        """
        if line == "EOF":
            return True
        self.perror(f"Unknown command: {line}")

    def get_all_commands(self) -> List[str]:
        """Get a list of all registered commands.

        :return: List of command names
        :rtype: List[str]
        """
        return list(self.command_info.keys())

    def get_visible_command_info(self) -> List[CommandInfo]:
        """Get a list of all registered commands that are visible and enabled.

        :return: List of visible command info objects
        :rtype: List[CommandInfo]
        """
        return [
            info for info in self.command_info.values()
            if not info.hidden
            and not info.disabled
        ]
    
    def get_visible_commands(self) -> List[str]:
        """Get a list of commands that are visible and enabled.

        Filters out commands marked as hidden or disabled.

        :return: List of visible command names
        :rtype: List[str]
        """
        return [info.name for info in self.get_visible_command_info()]
    
    @property
    def visible_prompt(self) -> str:
        """Read-only property to get the visible prompt with any ANSI style escape codes stripped.

        Used by transcript testing to make it easier and more reliable when users are doing things like coloring the
        prompt using ANSI color codes.

        :return: prompt stripped of any ANSI escape codes
        """
        return ANSI(self._render_rich_text(self.prompt)).value
    
    @property
    def completer(self) -> Completer:
        cmd_completer_options = {info.name: info.completer for info in self.get_visible_command_info()}
        shortcut_completers = [
            PrefixCompleter(shortcut, cmd_completer_options[name])  # type: ignore
            for shortcut, name in self.shortcuts.items()
            if name in cmd_completer_options and cmd_completer_options[name] is not None
        ]
        return merge_completers((NestedCompleter(cmd_completer_options), *shortcut_completers))
    
    def poutput(self, *objs, sep: str = " ", end: str = "\n", markup: Optional[bool] = None) -> None:
        self.console.print(*objs, sep=sep, end=end, markup=markup)

    def perror(self, *objs, sep: str = " ", end: str = "\n", markup: Optional[bool] = None) -> None:
        self.console.print(*objs, sep=sep, end=end, style="cmd.error", markup=markup)

    def psuccess(self, *objs, sep: str = " ", end: str = "\n", markup: Optional[bool] = None) -> None:
        self.console.print(*objs, sep=sep, end=end, style="cmd.success", markup=markup)

    def pwarning(self, *objs, sep: str = " ", end: str = "\n", markup: Optional[bool] = None) -> None:
        self.console.print(*objs, sep=sep, end=end, style="cmd.warning", markup=markup)

    def pexcept(self, *, show_locals: bool = False) -> None:
        self.console.print_exception(show_locals=show_locals)

    def print_topics(
        self, header: str, cmds: Optional[Sequence[str]], maxcol: Optional[int] = None
    ) -> None:
        if not cmds:
            return
        panel = Panel(Columns(cmds, width=maxcol), title=header, title_align="left")
        self.poutput(panel)

    def columnize(self, list: Optional[List[str]], displaywidth: Optional[int] = None) -> None:
        if list is None:
            self.console.print("<empty>")
            return
        self.console.print(
            Columns(list, width=displaywidth)
        )
    
    def _render_rich_text(self, text: Any) -> Any:
        if not isinstance(text, str) and is_formatted_text(text):
            return text
        with self.console.capture() as capture:
            self.console.print(text, end="")
        return capture.get()
    
    def _build_command_info(self, cmd: CommandFunc) -> CommandInfo:
        return build_cmd_info(cmd, self)

    def __init_subclass__(cls, **kwds: Any) -> None:
        for name in dir(cls):
            if not name.startswith(constants.COMMAND_FUNC_PREFIX):
                continue
            cls.__commands__.add(getattr(cls, name))


class Cmd(BaseCmd):
    __slots__ = []

    @auto_argument
    def do_help(self, topic: str = '', *, verbose: Arg[bool, "-v", "--verbose"] = False) -> None:  # noqa: F821
        """List available commands or provide detailed help for a specific command.
        """
        if not topic:
            return self._help_menu(verbose)
        help_topics = self._help_topics()

        # XXX check arg syntax
        if topic in help_topics and topic not in self.command_info:
            return self.poutput(self._format_help_menu(topic, help_topics[topic], verbose=verbose))
        elif topic not in self.command_info:
            return self.perror(f"Unknown command: {topic}")
        return self.poutput(self._format_help_text(self.command_info[topic], verbose))

    def _help_menu(self, verbose: bool = False) -> None:
        """Display the help menu showing available commands and help topics.

        Organizes commands by category if available, otherwise falls back to
        standard documented/undocumented grouping.

        :param verbose: If True, show more detailed help (not currently used)
        :type verbose: bool
        """
        cmds_cats = self._help_topics()
        cmds_undoc = [
            info.name
            for info in self.get_visible_command_info()
            if info.help_func is None
            and info.argparser is None
            and not info.category
            and not info.cmd_func.__doc__
        ]
        if self.doc_leader:
            self.poutput(self.doc_leader)
        if not cmds_cats:
            # No categories found, fall back to standard behavior
            self.poutput(
                self._format_help_menu(
                    self.doc_header,
                    self.get_visible_command_info(),
                    verbose=verbose,
                    style="cmd.help.doc",
                )
            )
        else:
            # Categories found, Organize all commands by category
            cmds_doc = [
                info
                for info in self.get_visible_command_info()
                if not info.category and info.name not in cmds_undoc
            ]
            layout = Layout()
            layout.split_column(
                *(Layout(self._format_help_menu(category, cmds_cats[category], verbose=verbose))
                for category in sorted(cmds_cats.keys()))
            )
            self.poutput(Panel(layout, title=self.doc_header))
            self.poutput(self._format_help_menu(self.default_category, cmds_doc, verbose=verbose))

        self.print_topics(self.misc_header, tuple(cmds_cats))
        self.print_topics(self.undoc_header, cmds_undoc)

    def _format_help_menu(self, title: str, cmds_info: List[CommandInfo], *, verbose: bool = False, style: Union[str, Style, None] = None) -> Any:
        cmds_info.sort(key=lambda info: info.name)
        return Panel(
            Columns(
                [
                    f"[cmd.help.name]{info.name}[/cmd.help.name] - {self._format_help_text(info)}"
                    if verbose else f"[cmd.help.name]{info.name}[/cmd.help.name]"
                    for info in cmds_info
                ]
            ),
            title=title,
            title_align="left",
            style=style or "cmd.help.menu"
        )

    def _format_help_text(self, cmd_info: CommandInfo, verbose: bool = False) -> str:
        """Format the help text for a command.

        :param cmd_info: The command info object
        :type cmd_info: CommandInfo
        :return: The formatted help text
        :rtype: str
        """
        if cmd_info.help_func is not None:
            return cmd_info.help_func(verbose)
        if cmd_info.argparser is not None:
            if verbose:
                return cmd_info.argparser.format_help()
            elif cmd_info.argparser.description is not None:
                return cmd_info.argparser.description
            else:
                return cmd_info.argparser.format_usage()
        if cmd_info.cmd_func.__doc__ is not None:
            return pydoc.getdoc(cmd_info.cmd_func.__doc__)
        else:
            return self.nohelp % (cmd_info.name,)

    def _help_topics(self) -> Dict[str, List[CommandInfo]]:
        cmds_cats = defaultdict(list)
        for info in self.get_visible_command_info():
            if info.category is not None:
                cmds_cats[info.category].append(info)
        return cmds_cats

    def do_exit(self, argv: List[str]) -> bool:
        """Exit the command loop.
        """
        return True
