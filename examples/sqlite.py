import sys
import sqlite3
from ptcmd import Cmd, auto_argument


class SQLiteApp(Cmd):
    DEFAULT_PROMPT  = "[cmd.prompt]sqlite[/cmd.prompt]> "

    @auto_argument
    def do_server(self):
        """Server management command"""
    
    @do_server.add_subcommand("db")
    def db(self):
        """Database management"""
    
    @db.add_subcommand("migrate")
    def migrate(self, version: str):
        """Perform database migration"""
        self.poutput(f"Migrating to version {version}...")
    
    @do_server.add_subcommand("cache")
    def cache(self):
        """Cache management"""
    
    @cache.add_subcommand("clear")
    def clear(self, confirm: bool = False):
        """Clear cache"""
        if confirm:
            self.poutput("Cache cleared")
        else:
            self.poutput("Please add --confirm flag to confirm the operation")


if __name__ == "__main__":
    sys.exit(SQLiteApp().cmdloop())
