# 参数解析

参数解析系统提供了从函数签名构建`ArgumentParser`的功能。这是一个相对独立的组件，通过与命令组件类`Command`集成来进入`ptcmd`框架。

## 基本示例

使用`@auto_argument`装饰器是最简单的声明式参数解析方式。它会自动分析函数的参数签名，并创建相应的`ArgumentParser`实例：

```python linenums="1"
from ptcmd import Cmd, auto_argument

class MyApp(Cmd):
    @auto_argument
    def do_hello(self, name: str = "World") -> None:
        """Hello World!"""
        self.poutput(f"Hello, {name}!")
```

在上面的例子中，`name`参数会自动转换为一个可选的位置参数，默认值为"World"。

## Argument类

`Argument` 是参数解析系统的核心类，用于以声明式方式定义命令行参数。它封装了 `argparse` 的参数配置，提供更 Pythonic 的接口。

### 基本用法

可以直接实例化 `Argument` 来定义参数：

```python linenums="1"
from ptcmd import Argument

# 创建一个简单的字符串参数
file_arg = Argument(
    "--file", 
    type=str,
    help="输入文件路径"
)

# 创建一个布尔标志参数
verbose_arg = Argument(
    "-v", "--verbose",
    action="store_true",
    help="启用详细输出"
)
```

### 参数配置

`Argument` 支持所有标准 `argparse` 参数配置，常用参数如下：

| 参数 | 描述 | 示例 |
|------|------|------|
| `action` | 指定参数动作 | `action="store_true"` |
| `nargs` | 参数数量 | `nargs='*'` |
| `const` | 与 `nargs` 或 `action` 配合使用的常量值 | `const="value"` |
| `default` | 默认值 | `default=0` |
| `type` | 参数类型转换函数 | `type=int` |
| `choices` | 允许的参数值列表 | `choices=["a", "b"]` |
| `required` | 是否必需 | `required=True` |
| `help` | 帮助文本 | `help="输入文件路径"` |
| `metavar` | 在帮助消息中显示的参数名称 | `metavar="FILE"` |
| `dest` | 存储参数值的目标属性名 | `dest="output_file"` |
| `version` | 与 `action="version"` 配合使用的版本号 | `version="1.0.0"` |

例如，定义一个需要多个输入文件的参数：

```python linenums="1"
files: Arg[
    list,
    "--files",
    {"nargs": "*", "type": str, "help": "输入文件列表"}
]
```

## 使用Arg类型注解

对于更复杂的参数定义，可以使用`Arg`类型提示。`Arg`允许指定参数的标志、帮助文本和其他属性：

```python linenums="1"
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

`Arg`的语法格式为：`Arg[类型, 参数标志..., {参数属性}]`

- 类型：参数的数据类型（如`str`、`int`、`float`、`bool`等）
- 参数标志：参数的命令行标志（如`"-v"`、`"--verbose"`）
- 参数属性：一个字典，包含参数的其他属性（如`help`、`choices`等），也可以使用一个`Argument`作为属性。

!!! note

    `Arg`实际上是适用于类型检查器的简单转换，运行时与`Argument`类完全等价。但通常推荐`Arg`仅用于类型注解

## 使用Annotated和Argument类型注解

如果希望更严格的遵照代码风格检查器，可以使用标准的`Annotated`和`Argument`以规避`Arg`的语法报错：

```python linenums="1"
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

但通过这种方式定义的参数无法获得参数字段补全，需要自行在`Argument`指定所有需要的字段。

### 参数忽略

当某些参数不需要出现在命令行界面时，可以使用 `IgnoreArg` 类型来标记该参数应被忽略：

```python linenums="1"
from ptcmd import Cmd, IgnoreArg, auto_argument

class App(Cmd):
    @auto_argument
    def do_process(
        self,
        input: str,
        internal_state: IgnoreArg[dict] = {}
    ) -> None:
        """处理输入数据，internal_state 仅用于内部状态管理"""
        # internal_state 不会出现在命令行参数中
        self.poutput(f"Processing {input}")
```

在这个例子中，`internal_state` 参数将被完全忽略，不会添加到命令行解析器中。

## 参数解析

`ptcmd`会根据参数的类型和位置自动推断参数的行为：

1. 位置参数：函数的位置参数会转换为命令行的位置参数
2. 可选参数：使用`*`分隔的关键字参数会转换为可选参数
3. 布尔参数：类型为`bool`的参数会自动转换为标志参数（`store_true`或`store_false`）
4. 默认值：参数的默认值会传递给`ArgumentParser`

### 自动推断

参数解析可以根据类型注解和参数特征自动推断合适的 `argparse` 配置，减少手动配置。以下是关键的自动推断规则：

#### 布尔类型自动转换

系统会根据布尔参数的默认值自动选择 `store_true` 或 `store_false` 动作：

```python linenums="1"
# 默认值为 False -> 自动使用 store_true
verbose: Arg[bool] = False  
# 生成: parser.add_argument("--verbose", action="store_true")

# 默认值为 True -> 自动使用 store_false
enabled: Arg[bool] = True   
# 生成: parser.add_argument("--enabled", action="store_false")

# 也可以显式指定标志
debug: Arg[bool, "-d", "--debug"] = False
# 生成: parser.add_argument("-d", "--debug", action="store_true")
```

#### 位置参数与关键字参数的自动处理

系统会根据参数在函数签名中的位置自动决定是位置参数还是可选参数：

```python linenums="1"
@auto_argument
def do_process(
    self,
    input_file: str,      # 位置参数（无默认值）
    output: str = "out",  # 位置参数（带默认值）
    *,
    verbose: bool = False # 关键字参数 -> 可选参数
) -> None:
    pass
```

- 位置参数：函数签名中的位置参数（无`*`分隔符）会转换为命令行位置参数
- 可选参数：使用`*`分隔的关键字参数会转换为命令行可选参数（必须使用`--`前缀）

#### Literal 类型的智能处理

当参数类型为 `Literal` 时，系统会自动设置 `choices`，并根据需要调整参数行为：

```python linenums="1"
from typing import Literal

# 自动设置 choices
level: Literal["debug", "info", "warning", "error"]

# 与默认值结合
level: Literal["debug", "info", "warning", "error"] = "info"
# 生成: parser.add_argument("--level", choices=..., default="info")

# 与关键字参数结合（自动成为可选参数）
def do_set(
    self,
    *,
    level: Literal["debug", "info"] = "info"
) -> None:
    pass
# 生成: parser.add_argument("--level", ...)
```

需要注意的是，如果在 `Argument` 中显式指定了 `choices` 参数，将覆盖 `Literal` 类型自动推导的选项：

#### 默认值的自动处理

默认值会直接影响参数的行为：

```python linenums="1"
# 位置参数带默认值 -> 变为可选位置参数
def do_example(self, file: str = "default.txt") -> None:
    pass
# 生成: parser.add_argument("file", nargs="?", default="default.txt")

# 关键字参数带默认值 -> 标准可选参数
def do_example(self, *, count: int = 1) -> None:
    pass
# 生成: parser.add_argument("--count", type=int, default=1)
```

### 处理未注解的参数

当函数参数未使用 `Arg` 或 `Argument` 进行注解时，`build_parser` 提供了三种处理模式，通过 `unannotated_mode` 参数控制：

- **strict**：严格模式，遇到未注解的参数时抛出 `TypeError`
- **autoconvert**：自动转换模式，尝试根据类型注解推断参数配置
- **ignore**：忽略模式，跳过未注解的参数

`@auto_argument` 装饰器默认使用**autoconvert**模式。在自动推断模式下，未被注解的参数`x: Tp`会被视为`x: Arg[Tp]`以自动推断参数信息。

```python linenums="1"
@auto_argument(unannotated_mode="autoconvert")
def do_convert(self, x: int, *, y: str = "y") -> None:
    ...
```

在 `autoconvert` 模式下，以上的代码会被视为

```python linenums="1"
@auto_argument(unannotated_mode="autoconvert")
def do_convert(self, x: Arg[int], *, y: Arg[str] = "y") -> None:
    ...
```

经过自动参数推断后，以上代码最终会转换为

```python linenums="1"
@auto_argument(unannotated_mode="autoconvert")
def do_convert(self, x: Annotated[int, Argument("x", type=int)], *, y: Annotated[str, Argument("-y", type=str, default="y")] = "y") -> None:
    ...
```

## 独立使用参数解析

参数解析
