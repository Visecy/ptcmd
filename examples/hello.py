import sys
from ptcmd import Cmd, auto_argument

class MyApp(Cmd):
    @auto_argument
    def do_hello(self, name: str = "World") -> None:
        """Hello World!"""
        self.poutput(f"Hello, {name}!")

if __name__ == "__main__":
    sys.exit(MyApp().cmdloop())
