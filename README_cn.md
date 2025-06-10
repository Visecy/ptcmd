# ptcmd

[![License](https://img.shields.io/github/license/Visecy/ptcmd.svg)](LICENSE)
[![PyPI](https://img.shields.io/pypi/v/ptcmd.svg)](https://pypi.python.org/pypi/ptcmd)
[![Build Status](https://github.com/Visecy/ptcmd/actions/workflows/test_cov.yml/badge.svg)](https://github.com/Visecy/ptcmd/actions)
![PyPI - Downloads](https://img.shields.io/pypi/dw/ptcmd)
![Python Version](https://img.shields.io/badge/python-3.8%20|%203.9%20|%203.10%20|%203.11%20|%203.12-blue.svg)

一个现代化的基于`prompt_toolkit`的交互式命令行应用程序构建库

**语言: [English](README.md)/中文**

## 1. 特性

- 🚀 基于`prompt_toolkit`构建，提供强大的交互式体验
- 📝 自动参数解析和补全
- 🌈 支持富文本输出(使用`rich`库)
- ⚡ 原生支持异步命令
- 🔍 内置命令补全和快捷键支持

## 2. 安装

从Pypi安装：

```bash
pip install ptcmd
```

或从源码安装：

```bash
git clone https://github.com/Visecy/ptcmd.git
cd ptcmd
make install
```

## 3. 快速开始

创建一个简单的简单的命令行应用：

```python
import sys
from ptcmd import Cmd

class MyApp(Cmd):
    def do_hello(self, argv: list[str]) -> None:
        """Hello World!"""
        if argv:
            name = argv[0]
        else:
            name = "World"
        self.poutput(f"Hello, {name}!")

if __name__ == "__main__":
    sys.exit(MyApp().cmdloop())
```

在这个简单的示例中:

1. 我们创建了一个继承自`Cmd`的类`MyApp`
2. 定义了一个名为`hello`的命令方法`do_hello`
3. 该命令接受一个可选的参数作为名字
4. 如果没有提供参数,默认使用"World"
5. 使用`self.poutput()`方法输出问候语
6. 最后通过`cmdloop()`方法启动交互式命令行界面

这个示例展示了ptcmd最基本的用法,包括:

- 命令定义方式
- 参数处理
- 输出显示
- 程序启动方式

运行程序后，输入`hello`命令即可体验：

```
(Cmd) hello
Hello, World!
(Cmd) hello Alice
Hello, Alice!
```

## 4. 高级功能

### 4.1 自动参数解析

对于复杂一些的命令，通常情况下，我们需要使用`argparse`库来解析命令行参数。`ptcmd`提供了一个更加简便的参数解析方式，允许通过函数参数及类型注解自动构建命令行参数解析。这可以通过在函数定义中使用`auto_argument`装饰器来实现。

```python
from ptcmd import Cmd, Arg, auto_argument

class MathApp(Cmd):
    @auto_argument
    def do_add(
        self, 
        x: float, 
        y: float,
        *,
        verbose: Arg[bool, "-v", "--verbose"] = False
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
        """两数相加"""
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

> 注意：如果想使函数参数被推断为可选命令行参数，需要将函数参数类型设置为强制关键字参数。

### 4.2 富文本输出

`ptcmd`通过`rich`库实现富文本输出。`Cmd`类的`poutput()`方法封装了`rich.Console`对象，并使用`Console.print()`方法进行输出。

```python
class RichApp(Cmd):
    def do_hello(self, argv: list[str]) -> None:
        # 使用rich mackup文本进行输出
        self.poutput(f"[bold blue]Hello, World![/bold blue]")
```

或者直接使用`self.console`对象进行更为复杂的富文本输出：

```python
class RichApp(Cmd):
    def do_hello(self, argv: list[str]) -> None:
        with self.console.pager(styles=True):
            self.console.print("Hello, World!", style="bold blue")
```

### 4.3 子命令支持

对于使用了自动参数解析特性的命令函数，`ptcmd`允许以简单的方式为其添加任意多级子命令。命令函数的执行顺序为从根命令开始，依次执行。

1. 一级子命令示例：

```python
from ptcmd import Cmd, auto_argument

class App(Cmd):
    @auto_argument
    def do_math(self):
        """数学运算命令集"""
        
    @do_math.add_subcommand("add")
    def add(self, x: float, y: float):
        """加法运算"""
        self.poutput(f"{x} + {y} = {x + y}")

    @do_math.add_subcommand("sub")
    def sub(self, x: float, y: float):
        """减法运算"""
        self.poutput(f"{x} - {y} = {x - y}")
```

使用方式：
```
(Cmd) math add 5 3
5.0 + 3.0 = 8.0
(Cmd) math sub 5 3
5.0 - 3.0 = 2.0
```

2. 多级子命令示例：

```python
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

使用方式：
```
(Cmd) server db migrate v1.2.0
正在迁移到版本 v1.2.0...
(Cmd) server cache clear --confirm
缓存已清除
```

### 4.4 异步命令支持

```python
import aiohttp
from ptcmd import Cmd, auto_argument

class AsyncApp(Cmd):
    @auto_argument
    async def do_get(self, url: str):
        """获取URL内容"""
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as resp:
                self.poutput(await resp.text(), markup=False)
```

## 5. 库比较

以下是cmd、cmd2和ptcmd三个库的优劣势比较：

| 特性                 | cmd (标准库)  | cmd2                            | ptcmd                    |
| -------------------- | ------------- | ------------------------------- | ------------------------ |
| **功能丰富度** | 基础功能      | 功能最丰富                      | 功能较为丰富             |
| **学习曲线**   | 简单          | 中等                            | 中等                     |
| **交互体验**   | 基础          | 良好                            | 优秀(基于prompt_toolkit) |
| **自动补全**   | 无            | 支持                            | 支持                     |
| **参数解析**   | 需手动处理    | 需要自行构建`ArgumentParser` | 自动解析                 |
| **异步支持**   | 无            | 无                              | 原生支持                 |
| **富文本输出** | 无            | 使用`cmd2.ansi`模块          | 使用`rich`库          |
| **依赖项**     | 无            | 较多                            | 最多                     |
| **性能**       | 高            | 中等                            | 中等                     |
| **适用场景**   | 简单交互式CLI | 复杂交互式CLI                   | 现代化交互式CLI          |

主要优势：

- **cmd**: Python标准库，无需额外依赖，适合简单CLI应用
- **cmd2**: 功能全面，社区支持好，兼容`cmd`，适合需要丰富功能的传统CLI
- **ptcmd**: 提供最佳交互体验，原生异步支持，适合现代化CLI应用

## 6. 相关项目

- [prompt_toolkit](https://github.com/prompt-toolkit/python-prompt-toolkit)：一个用于构建交互式命令行应用程序的Python库。
- [rich](https://github.com/Textualize/rich)：一个用于格式化文本和输出到终端的Python库。
- [typer](https://github.com/tiangolo/typer)：一个用于构建命令行应用程序的Python库。
- [cmd2](https://github.com/python-cmd2/cmd2)：一个用于在 Python 中构建交互式命令行应用程序的工具。它的目标是让开发人员可以快速轻松地构建功能丰富且用户友好的交互式命令行应用。
- [argparse](https://docs.python.org/3/library/argparse.html)：Python标准库，用于解析命令行参数和选项。
- [cmd](https://docs.python.org/3/library/cmd.html)：Python标准库，用于构建交互式命令行应用程序。

## 7. 特别鸣谢

- [cmd2](https://github.com/python-cmd2/cmd2)：提供了项目的灵感来源，命令自动补全部分逻辑同样参考此项目。
- [Cline](https://cline.bot/)：帮助我快速开发项目原型并完善文档及测试用例。

## 8. 许可证

本项目使用Apache License 2.0许可证 - 详情请参阅[LICENSE](LICENSE)文件。
