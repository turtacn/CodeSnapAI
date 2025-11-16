# 插件开发指南

## 插件系统概述
CodeSage 支持通过插件扩展 CLI 命令。插件是标准 Python 模块，实现特定接口即可被自动加载。

## 插件结构
```

.codesage/plugins/
├── my_plugin.py
└── another_plugin.py

```

## 最小插件示例
```python
# .codesage/plugins/hello_plugin.py
import click

def register_command(cli_group: click.Group):
    """插件入口函数，必须实现"""

    @cli_group.command('hello')
    @click.option('--name', default='World', help='Name to greet')
    def hello(name):
        """Say hello"""
        click.echo(f'Hello, {name}!')
```

**使用**:
```bash
codesage hello --name Alice
# 输出: Hello, Alice!
```

## 插件元数据
```python
__name__ = "my_plugin"
__version__ = "1.0.0"
__description__ = "My custom CodeSage plugin"
```

## 访问 CodeSage 核心功能
```python
from codesage.core.parser import ParserManager
from codesage.core.analyzer import AnalysisEngine

def register_command(cli_group):
    @cli_group.command('custom-analyze')
    @click.argument('path')
    def custom_analyze(path):
        # 使用 CodeSage 核心功能
        parser = ParserManager()
        ast = parser.parse_file(path, 'python')
        # 自定义分析逻辑...
```

## 插件最佳实践
1. **错误处理**: 使用 try-except 捕获异常
2. **参数验证**: 使用 click 的验证功能
3. **日志记录**: 使用 Python logging 模块
4. **配置支持**: 读取 .codesage.yaml 配置

## 示例插件：代码格式检查器
```python
# .codesage/plugins/linter_plugin.py
import click
import subprocess

def register_command(cli_group):
    @cli_group.command('lint')
    @click.argument('path', type=click.Path(exists=True))
    @click.option('--fix', is_flag=True, help='Auto-fix issues')
    def lint(path, fix):
        """Run linter on codebase"""
        cmd = ['pylint', path]
        if fix:
            cmd.append('--fix')

        result = subprocess.run(cmd, capture_output=True, text=True)
        click.echo(result.stdout)

        if result.returncode != 0:
            click.secho('Linting failed!', fg='red')
            raise click.Abort()
        else:
            click.secho('Linting passed!', fg='green')
```

## 发布插件
1. 创建 GitHub 仓库
2. 添加 README 和示例
3. 提交到 CodeSage 插件索引（待实现）
