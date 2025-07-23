# What is an Interactive Command-Line Application

## Core Concepts

An Interactive Command-Line Application is a type of command-line program that allows users to interact with the program in real-time. Unlike traditional command-line applications, which read all input at once and terminate after producing output, interactive command-line applications run continuously, waiting for user commands and responding immediately to them. It's like a conversation between the user and the computer: the user continuously issues commands, and the program responds with corresponding results based on these commands.

Take the Python interpreter's interactive mode as an example. When you enter `python` in the command line and press enter, you enter Python's interactive environment (REPL, Read-Eval-Print Loop), where the prompt is usually `>>>`. Here, you can input Python code line by line, and the interpreter will execute your code immediately and return the result. For example, if you input `print("Hello, World!")`, the interpreter will immediately output `Hello, World!`. This interaction is immediate, allowing users to decide what command to input next based on the previous command's result, just like having a real-time conversation with the program.

Another example is the interactive command-line tools of database clients, like the MySQL command-line client. After logging into the MySQL client, users can enter various SQL statements to query and modify the database. Each time a valid SQL command is entered, the client executes it and returns the corresponding query result or operation feedback. If querying data, it displays the matching rows; if performing data insertion, it indicates whether the operation was successful. This continuous interaction process allows users to perform data operations and management step by step based on the current state of the database.

## Comparison with Standard Command-Line Programs

The core difference between interactive command-line applications and standard command-line programs lies in **state management**. Interactive command-line applications maintain context state during operation without relying on external files or other methods to pass state. In contrast, each execution of a standard command-line program is an independent single operation that requires explicit state passing.

Therefore, interactive command-line applications are more suitable for scenarios that require maintaining context state, such as various management tools that rely on network sessions or debug tools that depend on process state. Standard command-line programs are more suitable for batch processing scenarios, such as file conversion, data processing, etc.

## Interaction Languages

Unlike standard command-line applications that uniformly use terminal syntax, interactive command-line applications on the market often use different languages for interaction. For example, Python's REPL uses Python directly for interaction; gdb has its own custom interaction language for debugging programs; database clients generally use SQL for interaction.

```py
>>> def factorial(n: int) -> int:
...     if n < 2:
...         return 1
...     return n * factorial(n - 1)
...
>>> factorial(5)
120
```

Some interactive command-line applications use terminal-like languages for user interaction, such as sftp. These programs resemble terminals in form but use custom commands that are not compatible with standard terminals. This approach is more intuitive for users, reducing the learning curve for syntax understanding.

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

## Developing Interactive Command-Line Applications

For interactive command-line applications that use custom interaction languages, developers often need to implement their own syntax parsing, which increases development difficulty. Applications that use terminal-like interaction languages have more existing tools available, making development easier. This is also the direction supported by `ptcmd`.

Since we're using terminal-like interaction languages, can we directly reuse the development toolchain of command-line applications? Undoubtedly, the command-line development toolchain is very mature, with many Python libraries ranging from the standard library's `argparse` to third-party libraries like `click` and `typer`, all allowing developers to quickly build complex command-line applications with multi-level subcommands. However, directly using the command-line development toolchain to create interactive command-line applications presents several problems:

1. Command-line applications are often designed to exit when encountering errors, which doesn't align with the needs of interactive command-line applications. This behavior is deeply rooted in their implementation and is difficult to change through configuration.
2. The completion mechanisms of command-line applications are developed for terminal environments and cannot be applied to interactive environments.

For interactive applications, Python actually provides a standard library `cmd` that allows developers to create interactive command-line applications by defining a class that inherits from `cmd.Cmd` and implementing corresponding methods.

```py
import sys
import cmd

class MyCmd(cmd.Cmd):
    def do_hello(self, args: str) -> None:
        print("Hello, world!")

if __name__ == '__main__':
    sys.exit(MyCmd().cmdloop())
```

However, the `cmd` library requires manual parameter parsing, doesn't support multi-level subcommands, and only provides completion for command names. This is insufficient for modern interactive applications. The third-party library `cmd2` addresses some of these issues. As an extension of the `cmd` library, `cmd2` is compatible with `cmd` while providing richer features, such as full command completion via `ArgumentParser`.

`cmd2` can meet most needs for interactive applications, but still has some shortcomings:

1. Subcommand support is limited; it doesn't support arbitrary multi-level subcommands.
2. Command argument parsing isn't intelligent enough, requiring manual construction of `ArgumentParser`, which results in significant boilerplate code.
3. Rich text support is lacking; it requires library-specific construction methods and doesn't support more universal libraries like `rich` (though version 3.X has migrated to `rich`).

Therefore, `ptcmd` was born, providing developers with a more modern solution for building interactive command-line applications.
