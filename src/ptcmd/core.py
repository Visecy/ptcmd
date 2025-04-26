import asyncio
import pydoc
import shlex
import sys
from asyncio import iscoroutine
from collections import defaultdict
from subprocess import run
from typing import Any, Callable, ClassVar, Coroutine, Dict, List, Optional, Set, TextIO, Tuple, TypeVar, Union, cast

from prompt_toolkit.application import create_app_session
from prompt_toolkit.completion import Completer, NestedCompleter
from prompt_toolkit.formatted_text import ANSI, is_formatted_text
from prompt_toolkit.input import Input, create_input
from prompt_toolkit.lexers import PygmentsLexer
from prompt_toolkit.output import Output, create_output
from prompt_toolkit.patch_stdout import StdoutProxy
from prompt_toolkit.shortcuts.prompt import CompleteStyle, PromptSession
from pygments.lexers.shell import BashLexer
from rich.columns import Columns
from rich.console import Console
from rich.layout import Layout
from rich.panel import Panel
from rich.style import Style
from rich.theme import Theme

from .argument import Arg
from .completer import MultiPrefixCompleter
from .command import auto_argument
from .info import CommandInfo, CommandLike, build_cmd_info, set_info
from .theme import DEFAULT as DEFAULT_THEME


_T = TypeVar("_T")


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
    """Base class for command line interfaces in ptcmd.

    This class provides the core functionality for building interactive command-line
    applications with features including:
    - Command registration and execution
    - Argument parsing and completion
    - Rich text output formatting
    - Command history and shortcuts
    - Help system integration

    The BaseCmd class is designed to be subclassed to create custom command-line
    interfaces. Subclasses can register commands using the @command decorator.
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
        "complete_style",
    ]
    __commands__: ClassVar[Set[CommandLike]] = set()

    COMMAND_FUNC_PREFIX: ClassVar[str] = "do_"
    HELP_FUNC_PREFIX: ClassVar[str] = "help_"

    DEFAULT_PROMPT: ClassVar[Any] = "([cmd.prompt]Cmd[/cmd.prompt]) "
    DEFAULT_SHORTCUTS: ClassVar[Dict[str, str]] = {}

    def __init__(
        self,
        stdin: Optional[TextIO] = None,
        stdout: Optional[TextIO] = None,
        *,
        session: Optional[Union[PromptSession, Callable[[Input, Output], PromptSession]]] = None,
        console: Optional[Console] = None,
        theme: Optional[Theme] = None,
        prompt: Any = None,
        shortcuts: Optional[Dict[str, str]] = None,
        intro: Optional[Any] = None,
        complete_style: CompleteStyle = CompleteStyle.READLINE_LIKE,
    ) -> None:
        """Initialize the BaseCmd instance with configuration options.

        :param stdin: Input stream (default: sys.stdin)
        :type stdin: Optional[TextIO]
        :param stdout: Output stream (default: sys.stdout)
        :type stdout: Optional[TextIO]
        :param session: Prompt session instance or factory (default: creates new session)
        :type session: Optional[Union[PromptSession, Callable[..., PromptSession]]]
        :param console: Rich console instance (default: creates new console)
        :type console: Optional[Console]
        :param theme: Rich theme for styling output (default: DEFAULT_THEME)
        :type theme: Optional[Theme]
        :param prompt: Command prompt display (default: DEFAULT_PROMPT)
        :type prompt: Any
        :param shortcuts: Command shortcut mappings (default: DEFAULT_SHORTCUTS)
        :type shortcuts: Optional[Dict[str, str]]
        :param intro: Introductory message shown at startup
        :type intro: Optional[Any]
        :param complete_style: Style for completion menu (default: CompleteStyle.READLINE_LIKE)
        :type complete_style: CompleteStyle
        :param doc_leader: Header text for help output (default: "")
        """
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
        self.complete_style = complete_style
        self.intro = intro
        # If any command has been categorized, then all other commands that haven't been categorized
        # will display under this section in the help output.
        self.default_category = "Uncategorized"

        if self.stdin.isatty():
            input = create_input(self.stdin)
            output = create_output(self.raw_stdout)
            with create_app_session(input, output):
                if callable(session):
                    self.session = session(input, output)
                else:
                    self.session = session or PromptSession(input=input, output=output)
                self.stdout = cast(TextIO, StdoutProxy(raw=True, sleep_between_writes=0.01))
        else:
            self.stdout = self.raw_stdout
            self.session = session if isinstance(session, PromptSession) else None
        self.console = console or Console(file=self.stdout, theme=self.theme)

        self.cmdqueue = []
        self.lastcmd = ""
        self.command_info = {info.name: info for info in map(self._build_command_info, self.__commands__)}

    def cmdloop(self, intro: Optional[Any] = None) -> None:
        """Start the command loop for synchronous execution.

        This is the main entry point for running the command processor.
        It wraps the async cmdloop_async() method in an asyncio.run() call.

        :param intro: Optional introductory message to display at startup
        :type intro: Optional[Any]
        """
        return asyncio.run(self.cmdloop_async(intro))

    async def cmdloop_async(self, intro: Optional[Any] = None) -> None:
        """Asynchronous command loop that processes user input.

        :param intro: Optional introductory message to display at startup
        :type intro: Optional[Any]
        """
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
                    try:
                        line = await self.input_line()
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

    async def input_line(self) -> str:  # pragma: no cover
        """Get a command line from the user.

        :return: The input line from the user
        :rtype: str
        """
        if self.session is None:
            loop = asyncio.get_running_loop()
            line = await loop.run_in_executor(None, self.stdin.readline)
            if not line:
                raise EOFError
            return line.rstrip("\r\n")
        prompt = self._render_rich_text(self.prompt)
        if isinstance(prompt, str):
            prompt = ANSI(prompt)
        return await self.session.prompt_async(
            prompt,
            completer=self.completer,
            lexer=PygmentsLexer(BashLexer),
            complete_in_thread=True,
            complete_style=self.complete_style,
        )

    def parseline(self, line: str) -> Union[Tuple[str, List[str], str], Tuple[None, None, str]]:
        """Parse the input line into command name and arguments.

        This method handles:
        1. Stripping whitespace from the input line
        2. Processing command shortcuts (e.g., '?' -> 'help')
        3. Tokenizing the command line into command and arguments
        4. Preserving the original line for history purposes

        :param line: The input command line to parse
        :type line: str
        :return: A tuple containing:
            - command name (str if valid command, None otherwise)
            - command arguments (List[str] if args exist, None otherwise)
            - original line (stripped of leading/trailing whitespace)
        :rtype: Union[Tuple[str, List[str], str], Tuple[None, None, str]]
        """
        line = line.strip()
        if not line:
            return None, None, line
        for shortcut, cmd_name in self.shortcuts.items():
            if line.startswith(shortcut):
                if cmd_name not in self.command_info:
                    return None, None, line
                line = f"{cmd_name} {line[len(shortcut) :]}"
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
        try:
            result = await _ensure_coroutine(info.cmd_func(arg))
        except (Exception, SystemExit):
            self.pexcept()
            return
        except KeyboardInterrupt:
            return
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
        return [info for info in self.command_info.values() if not info.hidden and not info.disabled]

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
        :rtype: str
        """
        return ANSI(self._render_rich_text(self.prompt)).value

    @property
    def completer(self) -> Completer:
        cmd_completer_options = {info.name: info.completer for info in self.get_visible_command_info()}
        shortcut_completers = {
            shortcut: cmd_completer_options[name] for shortcut, name in self.shortcuts.items() if name in cmd_completer_options
        }
        return MultiPrefixCompleter(shortcut_completers, NestedCompleter(cmd_completer_options))

    def poutput(self, *objs: Any, sep: str = " ", end: str = "\n", markup: Optional[bool] = None) -> None:
        self.console.print(*objs, sep=sep, end=end, markup=markup)

    def perror(self, *objs: Any, sep: str = " ", end: str = "\n", markup: Optional[bool] = None) -> None:
        self.console.print(*objs, sep=sep, end=end, style="cmd.error", markup=markup)

    def psuccess(self, *objs: Any, sep: str = " ", end: str = "\n", markup: Optional[bool] = None) -> None:
        self.console.print(*objs, sep=sep, end=end, style="cmd.success", markup=markup)

    def pwarning(self, *objs: Any, sep: str = " ", end: str = "\n", markup: Optional[bool] = None) -> None:
        self.console.print(*objs, sep=sep, end=end, style="cmd.warning", markup=markup)

    def pexcept(self, *, show_locals: bool = False) -> None:
        self.console.print_exception(show_locals=show_locals)

    def _render_rich_text(self, text: Any) -> Any:
        if not isinstance(text, str) and is_formatted_text(text):
            return text
        with self.console.capture() as capture:
            self.console.print(text, end="")
        return capture.get()

    def _build_command_info(self, cmd: CommandLike) -> CommandInfo:
        return build_cmd_info(cmd, self)

    def __repr__(self) -> str:
        """Return detailed command processor representation."""
        return (
            f"<{self.__class__.__name__} commands={len(self.command_info)} "
            f"prompt={self.visible_prompt!r} shortcuts={self.shortcuts}>"
        )

    def __init_subclass__(cls, **kwds: Any) -> None:
        for name in dir(cls):
            if not name.startswith(cls.COMMAND_FUNC_PREFIX):
                continue
            cls.__commands__.add(getattr(cls, name))


class Cmd(BaseCmd):
    __slots__ = []

    DEFAULT_SHORTCUTS: ClassVar[Dict[str, str]] = {"?": "help", "!": "shell", "@": "run_script"}

    def __init__(
        self,
        stdin: Optional[TextIO] = None,
        stdout: Optional[TextIO] = None,
        *,
        session: Optional[Union[PromptSession, Callable[[Input, Output], PromptSession]]] = None,
        console: Optional[Console] = None,
        theme: Optional[Theme] = None,
        prompt: Any = None,
        shortcuts: Optional[Dict[str, str]] = None,
        intro: Optional[Any] = None,
        complete_style: CompleteStyle = CompleteStyle.READLINE_LIKE,
        doc_leader: str = "",
        doc_header: str = "Documented commands (type help <topic>):",
        misc_header: str = "Miscellaneous help topics:",
        undoc_header: str = "Undocumented commands:",
        nohelp: str = "No help on %s",
    ) -> None:
        """Initialize the BaseCmd instance with configuration options.

        :param stdin: Input stream (default: sys.stdin)
        :type stdin: Optional[TextIO]
        :param stdout: Output stream (default: sys.stdout)
        :type stdout: Optional[TextIO]
        :param session: Prompt session instance or factory (default: creates new session)
        :type session: Optional[Union[PromptSession, Callable[..., PromptSession]]]
        :param console: Rich console instance (default: creates new console)
        :type console: Optional[Console]
        :param theme: Rich theme for styling output (default: DEFAULT_THEME)
        :type theme: Optional[Theme]
        :param prompt: Command prompt display (default: DEFAULT_PROMPT)
        :type prompt: Any
        :param shortcuts: Command shortcut mappings (default: DEFAULT_SHORTCUTS)
        :type shortcuts: Optional[Dict[str, str]]
        :param intro: Introductory message shown at startup
        :type intro: Optional[Any]
        :param complete_style: Style for completion menu (default: CompleteStyle.READLINE_LIKE)
        :type complete_style: CompleteStyle
        :param doc_leader: Header text for help output (default: "")
        :type doc_leader: str
        :param doc_header: Header for documented commands section (default: "Documented commands...")
        :type doc_header: str
        :param misc_header: Header for miscellaneous help topics (default: "Miscellaneous help...")
        :type misc_header: str
        :param undoc_header: Header for undocumented commands (default: "Undocumented commands:")
        :type undoc_header: str
        :param nohelp: Message shown when no help is available (default: "No help on %s")
        :type nohelp: str
        """
        super().__init__(
            stdin=stdin,
            stdout=stdout,
            session=session,
            console=console,
            theme=theme,
            prompt=prompt,
            shortcuts=shortcuts,
            intro=intro,
            complete_style=complete_style,
        )
        self.doc_leader = doc_leader
        self.doc_header = doc_header
        self.misc_header = misc_header
        self.undoc_header = undoc_header
        self.nohelp = nohelp

    @auto_argument
    def do_help(self, topic: str = "", *, verbose: Arg[bool, "-v", "--verbose"] = False) -> None:  # noqa: F821,B002
        """List available commands or provide detailed help for a specific command"""
        if not topic:
            return self._help_menu(verbose)
        help_topics = self._help_topics()

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
            info
            for info in self.get_visible_command_info()
            if info.help_func is None and info.argparser is None and not info.category and not info.cmd_func.__doc__
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
            cmds_doc = [info for info in self.get_visible_command_info() if not info.category and info not in cmds_undoc]
            layout = Layout()
            layout.split_column(
                *(
                    Layout(self._format_help_menu(category, cmds_cats[category], verbose=verbose))
                    for category in sorted(cmds_cats.keys())
                )
            )
            self.poutput(Panel(layout, title=self.doc_header))
            self.poutput(self._format_help_menu(self.default_category, cmds_doc, verbose=verbose, style="cmd.help.doc"))
            self.poutput(
                Panel(
                    Columns([f"[cmd.help.name]{name}[/cmd.help.name]" for name in cmds_cats]),
                    title=self.misc_header,
                    title_align="left",
                    style="cmd.help.misc",
                )
            )

        if cmds_undoc:
            self.poutput(self._format_help_menu(self.undoc_header, cmds_undoc, verbose=verbose, style="cmd.help.undoc"))

    def _format_help_menu(
        self, title: str, cmds_info: List[CommandInfo], *, verbose: bool = False, style: Union[str, Style, None] = None
    ) -> Any:
        cmds_info.sort(key=lambda info: info.name)
        return Panel(
            Columns(
                [
                    f"[cmd.help.name]{info.name}[/cmd.help.name] - {self._format_help_text(info)}"
                    if verbose
                    else f"[cmd.help.name]{info.name}[/cmd.help.name]"
                    for info in cmds_info
                ]
            ),
            title=title,
            title_align="left",
            style=style or "cmd.help.misc",
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
            return pydoc.getdoc(cmd_info.cmd_func)
        else:
            return self.nohelp % (cmd_info.name,)

    def _help_topics(self) -> Dict[str, List[CommandInfo]]:
        cmds_cats = defaultdict(list)
        for info in self.get_visible_command_info():
            if info.category is not None:
                cmds_cats[info.category].append(info)
        return cmds_cats

    def do_exit(self, argv: List[str]) -> bool:
        """Exit the command loop"""
        return True

    @set_info(hidden=True)
    def do_shell(self, argv: List[str]) -> None:
        """Run a shell command"""
        cmd = " ".join(argv)
        ret = run(cmd, shell=True)
        if ret.returncode != 0:
            self.perror(f"Command failed with exit code {ret.returncode}")
