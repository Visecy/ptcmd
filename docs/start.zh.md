# 快速开始

## 安装

从Pypi安装（推荐）：

```bash
pip install ptcmd
```

或从源码安装：

```bash
git clone https://github.com/Visecy/ptcmd.git
cd ptcmd
make install
```

如果希望运行单元测试，可以使用：

```bash
make develop test
```

如果想在本地构建文档，可以使用：
```bash
make develop docs
```

## 基本应用结构

ptcmd应用基本都遵循一个一致的模式：继承 `Cmd` 类，并使用 `do_` 前缀约定定义命令方法，最后创建实例并调用`cmdloop()`方法启动交互。

## 创建第一个应用

让我们从一个最简单的应用开始：

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

我们定义了一个名为`MyApp`的类，继承自`Cmd`，在类中定义了唯一的一个命令`hello`。现在我们可以运行这个脚本：

```
(Cmd) hello
Hello, World!
(Cmd) hello Alice
Hello, Alice!
(Cmd) exit
```

输入`hello`命令，我们就可以得到我们想要的输出结果，最后别忘记输入`exit`命令退出程序。

## 使用声明式参数解析

以上的示例其实有一点小问题，当传入多个参数时，命令会直接忽略后面的参数。这并不是一个好的实践。在函数中添加一些判断或者使用`argparse`来处理这种情况，不过这些方式都不够简洁，会产生大量的样板代码。

`ptcmd`提供了一种声明式参数解析的方式，可以通过分析函数的签名信息，自动进行参数解析。这需要使用`@auto_argument`装饰器来装饰命令方法：

```python
import sys
from ptcmd import Cmd, auto_argument

class MyApp(Cmd):
    @auto_argument
    def do_hello(self, name: str = "World") -> None:
        """Hello World!"""
        self.poutput(f"Hello, {name}!")

if __name__ == "__main__":
    sys.exit(MyApp().cmdloop())
```

现在我们通过更加简短的代码实现了功能更加完善的命令。现在你可以像使用命令行程序一样，使用`-h/--help`参数来获取命令信息：

```
(Cmd) hello
Hello, World!
(Cmd) hello Alice
Hello, Alice!
(Cmd) hello -h
Usage: hello [-h] [name]

Hello World!

Positional Arguments:
  name

Optional Arguments:
  -h, --help  show this help message and exit
```

## 下一步该做什么

- 观看[用户指南](./user_guide/index.md)以获取更详细的使用说明。
- 观看[示例](./examples/index.md)以获取更多示例。
- 观看[API 参考](./api/index.md)以获取详细的 API 定义。
