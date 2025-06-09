import sys
from ptcmd import Cmd
from typing import List


class MyApp(Cmd):
    def do_hello(self, argv: List[str]) -> None:
        """Hello World!"""
        if argv:
            name = argv[0]
        else:
            name = "World"
        self.poutput(f"Hello, {name}!")


if __name__ == "__main__":
    sys.exit(MyApp().cmdloop())
