import asyncio
import sys
from itertools import count
from typing import List

from ptcmd import Cmd


class Background(Cmd):
    """
    Background tasks
    """

    def preloop(self) -> None:
        self._task = asyncio.create_task(self.background())

    def postloop(self) -> None:
        if self.running:
            self._task.cancel()

    async def background(self) -> None:
        """
        Run background tasks
        """
        for seq in count():
            self.poutput(f"ping from background task ({seq=:03})")
            await asyncio.sleep(1)

    def do_ping(self, argv: List[str]) -> None:
        """
        Ping the background task
        """
        if self.running:
            self.poutput("pong from foreground task")
        else:
            self.perror("Background task is not running")

    def do_kill(self, argv: List[str]) -> None:
        """
        Kill the background task
        """
        if self.running:
            self.poutput("Killing background task")
            self._task.cancel()
        else:
            self.perror("Background task is not running")

    @property
    def running(self) -> bool:
        """
        Return True if the background task is running
        """
        return hasattr(self, "_task") and not self._task.done()



if __name__ == "__main__":
    sys.exit(Background().cmdloop())
