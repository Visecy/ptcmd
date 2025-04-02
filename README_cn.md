# ptcmd

[![License](https://img.shields.io/github/license/Visecy/ptcmd.svg)](LICENSE)
[![PyPI](https://img.shields.io/pypi/v/ptcmd.svg)](https://pypi.python.org/pypi/ptcmd)
[![Build Status](https://github.com/Visecy/ptcmd/actions/workflows/test_cov.yml/badge.svg)](https://github.com/Visecy/ptcmd/actions)
![PyPI - Downloads](https://img.shields.io/pypi/dw/ptcmd)
![Python Version](https://img.shields.io/badge/python-3.8%20|%203.9%20|%203.10%20|%203.11%20|%203.12-blue.svg)

一个现代化的基于 `prompt_toolkit`的交互式命令行应用程序构建库

**语言: [English](README.md)/中文**

## 特性

- 🚀 基于prompt_toolkit构建，提供强大的交互式体验
- 📝 自动参数解析和补全
- 🌈 支持富文本输出(使用rich库)
- ⚡ 原生支持异步命令
- 🔍 内置命令补全和快捷键支持

## 安装

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

## 快速开始

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

运行程序后，输入 `hello`命令即可体验：

```
(Cmd) hello
Hello, World!
(Cmd) hello Alice
Hello, Alice!
```

## 高级功能

### 自动参数解析

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
    ):
        """两数相加
        :param x: 第一个数
        :param y: 第二个数
        :param verbose: 显示详细输出
        """
        result = x + y
        if verbose:
            self.poutput(f"{x} + {y} = {result}")
        else:
            self.poutput(result)
```

### 异步命令支持

```python
import asyncio
from ptcmd import Cmd, auto_argument

class AsyncApp(Cmd):
    @auto_argument
    async def do_fetch(self, url: str):
        """获取URL内容"""
        import aiohttp
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as resp:
                self.poutput(await resp.text())
```

## 库比较

以下是cmd、cmd2和ptcmd三个库的优劣势比较：

| 特性 | cmd (标准库) | cmd2 | ptcmd |
|------|-------------|------|-------|
| **功能丰富度** | 基础功能 | 功能最丰富 | 功能较为丰富 |
| **学习曲线** | 简单 | 中等 | 中等 |
| **交互体验** | 基础 | 良好 | 优秀(基于prompt_toolkit) |
| **自动补全** | 无 | 支持 | 支持 |
| **参数解析** | 需手动处理 | 需要自行构建`ArgumentParser` | 自动解析 |
| **异步支持** | 无 | 无 | 原生支持 |
| **富文本输出** | 无 | 使用`cmd2.ansi`模块 | 使用`rich`库 |
| **依赖项** | 无 | 较多 | 最多 |
| **性能** | 高 | 中等 | 中等 |
| **适用场景** | 简单交互式CLI | 复杂交互式CLI | 现代化交互式CLI |

主要优势：
- **cmd**: Python标准库，无需额外依赖，适合简单CLI应用
- **cmd2**: 功能全面，社区支持好，适合需要丰富功能的传统CLI
- **ptcmd**: 提供最佳交互体验，原生异步支持，适合现代化CLI应用

## 相关项目

- [prompt_toolkit](https://github.com/prompt-toolkit/python-prompt-toolkit)：一个用于构建交互式命令行应用程序的Python库。
- [rich](https://github.com/Textualize/rich)：一个用于格式化文本和输出到终端的Python库。
- [typer](https://github.com/tiangolo/typer)：一个用于构建命令行应用程序的Python库。
- [cmd2](https://github.com/python-cmd2/cmd2)：一个用于在 Python 中构建交互式命令行应用程序的工具。它的目标是让开发人员可以快速轻松地构建功能丰富且用户友好的交互式命令行应用。
- [argparse](https://docs.python.org/3/library/argparse.html)：Python标准库，用于解析命令行参数和选项。
- [cmd](https://github.com/python/cpython/blob/3.12/Lib/cmd.py)：Python标准库，用于构建交互式命令行应用程序。

## 特别鸣谢

- [cmd2](https://github.com/python-cmd2/cmd2)：提供了项目的灵感来源，命令自动补全部分逻辑同样参考此项目。
- [Cline](https://cline.bot/)：帮助我快速开发项目原型并完善文档及测试用例。

## 许可证

本项目使用Apache License 2.0许可证 - 详情请参阅[LICENSE](LICENSE)文件。
