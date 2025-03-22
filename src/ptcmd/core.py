import shlex
from cmd import Cmd as _Cmd
from typing import IO, Any, List, Optional, cast

from prompt_toolkit import PromptSession
from prompt_toolkit.completion import WordCompleter
from prompt_toolkit.patch_stdout import StdoutProxy
from rich.console import Console
from rich.columns import Columns

from . import constants


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
                        line = self.session.prompt(self.prompt, completer=WordCompleter(self.get_all_commands()))
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
    
    def do_help(self, arg):
        'List available commands with "help" or detailed help with "help cmd".'
        if arg:
            # XXX check arg syntax
            try:
                func = getattr(self, 'help_' + arg)
            except AttributeError:
                try:
                    doc=getattr(self, 'do_' + arg).__doc__
                    if doc:
                        self.stdout.write("%s\n"%str(doc))
                        return
                except AttributeError:
                    pass
                self.stdout.write("%s\n"%str(self.nohelp % (arg,)))
                return
            func()
        else:
            names = self.get_names()
            cmds_doc = []
            cmds_undoc = []
            help = {}
            for name in names:
                if name[:5] == 'help_':
                    help[name[5:]]=1
            names.sort()
            # There can be duplicates if routines overridden
            prevname = ''
            for name in names:
                if name[:3] == 'do_':
                    if name == prevname:
                        continue
                    prevname = name
                    cmd=name[3:]
                    if cmd in help:
                        cmds_doc.append(cmd)
                        del help[cmd]
                    elif getattr(self, name).__doc__:
                        cmds_doc.append(cmd)
                    else:
                        cmds_undoc.append(cmd)
            self.stdout.write("%s\n"%str(self.doc_leader))
            self.print_topics(self.doc_header,   cmds_doc,   15,80)
            self.print_topics(self.misc_header,  list(help.keys()),15,80)
            self.print_topics(self.undoc_header, cmds_undoc, 15,80)

    def print_topics(self, header, cmds, cmdlen, maxcol):
        if cmds:
            self.stdout.write("%s\n"%str(header))
            if self.ruler:
                self.stdout.write("%s\n"%str(self.ruler * len(header)))
            self.columnize(cmds, maxcol-1)
            self.stdout.write("\n")

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
    
    def get_all_commands(self) -> List[str]:
        """Return a list of all commands"""
        return [
            name[len(constants.COMMAND_FUNC_PREFIX) :]
            for name in self.get_names()
            if name.startswith(constants.COMMAND_FUNC_PREFIX) and callable(getattr(self, name))
        ]

    def poutput(self, *objs, sep: str = ' ', end: str = '\n') -> None:
        self.console.print(*objs, sep=sep, end=end)
    
    

    # def get_visible_commands(self) -> List[str]:
    #     """Return a list of commands that have not been hidden or disabled"""
    #     return [
    #         command
    #         for command in self.get_all_commands()
    #         if command not in self.hidden_commands and command not in self.disabled_commands
    #     ]

