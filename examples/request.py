from typing import Any, Optional
from aiohttp import ClientSession
from ptcmd import Cmd, auto_argument


class RequestApp(Cmd):
    DEFAULT_PROMPT = "[cmd.prompt]request[/cmd.prompt]> "

    @auto_argument
    async def do_get(self, url: str, *, params: Optional[str] = None) -> None:
        """Send a GET request to the specified URL"""
        async with ClientSession() as session:
            async with session.get(url, params=params) as response:
                content = await response.text()
                self.poutput(f"Response from {url}:\n{content}")

    @auto_argument
    async def do_post(self, url: str, data: str) -> None:
        """Send a POST request to the specified URL with data"""
        async with ClientSession() as session:
            async with session.post(url, data=data) as response:
                content = await response.text()
                self.poutput(f"Response from {url}:\n{content}")


if __name__ == "__main__":
    RequestApp().cmdloop()
