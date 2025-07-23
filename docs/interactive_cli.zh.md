# 什么是交互式命令行应用

## 核心概念

交互式命令行应用（Interactive Command-Line Applications）是一种允许用户与程序进行实时交互的命令行程序。与传统的命令行应用（Command-Line Applications）不同，交互式命令行应用在执行过程中，并非一次性读取所有输入并产生输出后就结束运行，而是会持续运行，等待用户输入各种命令，并即时对这些命令做出响应。它就像是用户与计算机之间的一场对话，用户不断提出指令，程序则根据这些指令反馈相应的结果。

以常见的 Python 解释器的交互式模式为例，当你在命令行中输入python并回车后，会进入 Python 的交互式环境（REPL,Read-Eval-Print Loop），提示符通常为>>>。此时，你可以逐行输入 Python 代码，解释器会立即执行你输入的代码并返回结果。比如输入`print("Hello, World!")`，解释器会马上输出Hello, World!。这种交互是即时的，用户可以根据上一条命令的执行结果，灵活地决定下一条输入什么命令，就像在与程序进行实时交流一样。

再比如一些数据库客户端的交互式命令行工具，如 MySQL 的命令行客户端。用户登录到 MySQL 客户端后，可在命令行中输入各种 SQL 语句来查询、修改数据库。每输入一条有效的 SQL 命令，客户端就会执行该命令并返回相应的查询结果或操作反馈。如果查询数据，会显示符合条件的数据行；如果执行数据插入操作，会告知操作是否成功等。这种持续交互的过程，让用户能够根据数据库的当前状态，逐步深入地进行数据操作和管理。

## 与一般命令行程序对比

交互式命令行应用与一般命令行程序的核心区别在于**状态**，交互式命令行应用在运行过程中会保持上下文状态，不需要借助外部文件或其他方式来传递状态。而一般命令行程序每次执行都是独立的单次操作，需要显式传递状态。

因此，交互式命令行应用更适用于需要保持上下文状态的场景，如各种依赖于网络回话的管理工具或依赖进程状态的debug工具。而一般命令行程序更适用于需要批量处理的场景，如文件转换、数据处理等。

## 交互语言

与命令行应用统一使用终端语法不同，市面上的交互式命令行应用往往会使用不同的语言来实现。如Python的REPL就直接使用Python语言进行交互；gdb则有一套自定义的交互语言，用于调试程序；数据库客户端一般则使用SQL语言进行交互。

```py
>>> def factorial(n: int) -> int:
...     if n < 2:
...         return 1
...     return n * factorial(n - 1)
...
>>> factorial(5)
120
```

还有一部分交互式命令行应用则使用仿终端语言进行用户交互，如sftp。这种交互式命令行程序形式上类似于终端，但使用不与终端通用的自定义命令。这种方式更符合一般的使用习惯，减轻了用户在语法理解方面的上手难度。

```
sftp> ?
Available commands:
bye                                Quit sftp
cd path                            Change remote directory to 'path'
chgrp [-h] grp path                Change group of file 'path' to 'grp'
chmod [-h] mode path               Change permissions of file 'path' to 'mode'
chown [-h] own path                Change owner of file 'path' to 'own'
copy oldpath newpath               Copy remote file
cp oldpath newpath                 Copy remote file
df [-hi] [path]                    Display statistics for current directory or
                                   filesystem containing 'path'
exit                               Quit sftp
get [-afpR] remote [local]         Download file
help                               Display this help text
lcd path                           Change local directory to 'path'
lls [ls-options [path]]            Display local directory listing
lmkdir path                        Create local directory
ln [-s] oldpath newpath            Link remote file (-s for symlink)
lpwd                               Print local working directory
ls [-1afhlnrSt] [path]             Display remote directory listing
lumask umask                       Set local umask to 'umask'
mkdir path                         Create remote directory
progress                           Toggle display of progress meter
put [-afpR] local [remote]         Upload file
pwd                                Display remote working directory
quit                               Quit sftp
reget [-fpR] remote [local]        Resume download file
rename oldpath newpath             Rename remote file
reput [-fpR] local [remote]        Resume upload file
rm path                            Delete remote file
rmdir path                         Remove remote directory
symlink oldpath newpath            Symlink remote file
version                            Show SFTP version
!command                           Execute 'command' in local shell
!                                  Escape to local shell
?                                  Synonym for help
```

## 交互式命令行应用的开发

对于使用自定义交互语言的交互式命令行应用来说，交互式语言往往需要开发者自行进行语法解析，开发难度较高。而使用仿终端交互语言的应用有着更多的现有工具，开发难度较低。这也是`ptcmd`支持的方向。

既然使用了仿终端交互语言，那么能否直接复用命令行应用的开发工具链呢？毫无疑问，命令行的开发工具链的非常完备的，有很多的Python库，从标准库中的`argparse`，再到上层的`click`、`typer`等第三方库都允许开发者快速搭建复杂的包含多层子命令的命令行应用。但直接使用命令行开发工具链开发交互式命令行应用存在诸多问题。

1. 命令行应用往往被设计为在发现错误时直接退出，这不符合交互式命令行应用的需求。这种行为根植于实现底层，难以通过配置更改。
2. 命令行应用的补全机制都是针对于终端环境开发，无法应用到交互式环境中。

对于交互式应用，Python实际上也提供了一个标准库`cmd`，允许开发者通过定义一个类继承`cmd.Cmd`类，并实现相应的方法，来创建一个交互式命令行应用。

```py
import sys
import cmd

class MyCmd(cmd.Cmd):
    def do_hello(self, args: str) -> None:
        print("Hello, world!")

if __name__ == '__main__':
    sys.exit(MyCmd().cmdloop())
```

然而，`cmd`库需要用户手动进行参数解析，不支持多级子命令，仅支持对命令名进行补全。这对于现代的交互式应用来说并不足够。第三方库`cmd2`在一定程度上解决了这些问题，这是一个`cmd`库的扩展，在兼容`cmd`库的同时，提供了更丰富的功能，如完整的通过`ArgumentParser`的自动命令补全。

`cmd2`基本已经可以满足觉大多数的交互式应用需求，但仍然存在一些问题：

1. 对子命令的支持不够好，不支持任意多级子命令。
2. 命令的参数解析不够智能，需要手动构造`ArgumentParser`，这造成了大量样板代码。
3. 富文本支持不够好，需要使用库自定义的构造方式，不支持更加通用的`rich`库（目前在3.X版本已经迁移到`rich`）

因此，`ptcmd`诞生了，为开发者提供了更加现代化的交互式命令行构建方案。
