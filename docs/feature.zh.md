# 特性

本文档全面概述了`ptcmd`的核心功能和特色。它解释了该框架如何结合现代 Python库，创建强大的CLI开发体验。有关核心框架类的实现细节，请参阅核心框架。有关详细的用法模式和示例，请参阅示例和用法。

## 强大的交互体验

`ptcmd`基于现代化的交互库`prompt_toolkit`构建，提供超越基本文本输入输出的现代交互式命令行体验。该框架自动处理复杂的终端交互，提供补全和语法高亮。

![syntax_highlighting](/ptcmd/assets/syntax-highlighting.png)

## 声明式参数解析

`ptcmd`通过`@auto_argument`装饰器和`Arg`类型提示消除了样板参数解析代码。该系统自动根据函数签名生成`ArgumentParser`实例，使命令定义既简洁又类型安全。

```python
from ptcmd import Cmd, Arg, auto_argument

class MathApp(Cmd):
    @auto_argument
    def do_add(
        self, 
        x: float, 
        y: float,
        *,
        verbose: Arg[bool, "-v", "--verbose", {"help": "详细输出"}] = False
    ) -> None:
        """两数相加"""
        result = x + y
        if verbose:
            self.poutput(f"{x} + {y} = {result}")
        else:
            self.poutput(result)
```

以上示例等价于以下代码：

```python
from ptcmd import Cmd, Arg, auto_argument
from argparse import ArgumentParser

class MathApp(Cmd):
    def do_add(self, argv: list[str]) -> None:
        parser = ArgumentParser(prog="add", description="两数相加")
        parser.add_argument("x", type=float)
        parser.add_argument("y", type=float)
        parser.add_argument("-v", "--verbose", action="store_true")
        ns = parser.parse_args(argv)
        result = ns.x + ns.y
        if ns.verbose:
            self.poutput(f"{ns.x} + {ns.y} = {result}")
        else:
            self.poutput(result)
```

如果你正在使用类型检测器，使用`Arg`往往会被类型检查器视为错误，可以在行尾添加`# noqa: F821,F722,B002`让类型检查器忽略这些问题。如果你真的非常介意，可以`Annotated`与`Argument`来更加合法的声明参数，但这写起来更加麻烦，同时会失去一些自动推断特性。

```python
from typing import Annotated
from ptcmd import Cmd, Argument, auto_argument

class MathApp(Cmd):
    @auto_argument
    def do_add(
        self, 
        x: float, 
        y: float,
        *,
        verbose: Annotated[bool, Argument("-v", "--verbose", action="store_true")] = False
    ) -> None:
        """两数相加"""
        result = x + y
        if verbose:
            self.poutput(f"{x} + {y} = {result}")
        else:
            self.poutput(result)
```

## 富文本输出

`ptcmd`集成了`rich`库，提供高级的文本格式化、样式和布局功能。该框架封装了 `rich.Console`功能，同时保持与现有基于打印的代码的兼容性。

`Cmd`类向外暴露了`console`属性，该属性是一个`rich.Console`对象，用于打印富文本。也可以使用封装好的`poutput`、`pwarning`、`perror`等封装好的方法，间接通过`console`打印富文本。

```py
class RichApp(Cmd):
    def do_hello(self, argv: list[str]) -> None:
        # 使用rich mackup文本进行输出
        self.poutput(f"[bold blue]Hello, World![/bold blue]")
```

prompt部分支持使用`rich`或`prompt_toolkit`的富文本样式。

```py
class RichTextApp(Cmd):
    DEFAULT_PROMPT = "[cmd.prompt]rich[/cmd.prompt]> "

    @auto_argument
    def do_test_card(self) -> None:
        """show rich text"""
        self.poutput(make_test_card())
```

![test_card](/ptcmd/assets/test_card.png)

## 自动命令补全

`ptcmd`能够根据命令的提供的`ArgumentParser`实例信息，自动理解命令结构、参数类型和可用值，通过`prompt_toolkit`的`Completer`实现自动命令补全。

补全默认使用接近终端补全方式的`READLINE_LIKE`风格。

![auto_complete](/ptcmd/assets/completion.png)

也可以使用`prompt_toolkit`提供的`MULTI_COLUMN`补全风格。

![multi_column_completion](/ptcmd/assets/multi_column_completion.png)

## 任意多级子命令

`ptcmd`支持为一个命令添加任意多级子命令。

```py
from ptcmd import Cmd, auto_argument

class App(Cmd):
    @auto_argument
    def do_server(self):
        """服务器管理"""

    @do_server.add_subcommand("db")
    def db(self):
        """数据库管理"""

    @db.add_subcommand("migrate")
    def migrate(self, version: str):
        """执行数据库迁移"""
        self.poutput(f"正在迁移到版本 {version}...")

    @do_server.add_subcommand("cache")
    def cache(self):
        """缓存管理"""

    @cache.add_subcommand("clear")
    def clear(self, confirm: bool = False):
        """清除缓存"""
        if confirm:
            self.poutput("缓存已清除")
        else:
            self.poutput("请添加--confirm参数确认操作")
```

## 原生异步支持

得益于`prompt_toolkit`优秀的异步支持，`ptcmd`也原生支持异步命令。

```py
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
    async def do_post(self, url: str, data: Any) -> None:
        """Send a POST request to the specified URL with data"""
        async with ClientSession() as session:
            async with session.post(url, data=data) as response:
                content = await response.text()
                self.poutput(f"Response from {url}:\n{content}")


if __name__ == "__main__":
    RequestApp().cmdloop()
```
