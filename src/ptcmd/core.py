import shlex
from cmd import Cmd as _Cmd
from typing import IO, Any, Optional, cast

from prompt_toolkit import PromptSession
from prompt_toolkit.completion import WordCompleter
from prompt_toolkit.patch_stdout import StdoutProxy
from rich.console import Console
from rich.columns import Columns


class Cmd(_Cmd):
    def __init__(
        self,
        completekey: str = "tab",
        session: Optional[PromptSession] = None,
        console: Optional[Console] = None,
    ) -> None:
        self.session = session or PromptSession()
        self.console = console or Console(file=cast(IO[str], StdoutProxy(raw=True)))
        self.cmdqueue = []
        self.completekey = completekey
    
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
                    try:
                        line = self.session.prompt(self.prompt)
                    except KeyboardInterrupt:
                        self.console.print("^C")
                        continue
                line = self.precmd(line)
                stop = self.onecmd(line)
                stop = self.postcmd(stop, line)
        finally:
            self.postloop()
    
    def default(self, line: str) -> None:
        self.console.print(f"[red]Unknown command: {line}[/red]")
    
    def columnize(self, list: Optional[list[str]], displaywidth: Optional[int] = None) -> None:
        if list is None:
            self.console.print("<empty>")
            return
        self.console.print(
            Columns(
                [f"[bold]{item}[/bold]" for item in list],
                width=displaywidth,
            )
        )
