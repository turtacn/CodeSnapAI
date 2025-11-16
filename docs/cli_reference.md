# CLI 命令参考手册

## 安装
```bash
pip install codesage
```

## 快速开始
```bash
# 初始化配置
codesage config init

# 分析代码
codesage analyze ./src

# 创建快照
codesage snapshot create

# 对比快照
codesage diff v1 v2
```

## 命令详解

### codesage analyze
**用途**: 分析代码库并生成报告

**语法**:
```
codesage analyze <PATH> [OPTIONS]
```

**选项**:
- `--language, -l`: 指定分析语言（可多次使用）
- `--exclude, -e`: 排除模式（支持 glob）
- `--output, -o`: 输出文件路径
- `--format, -f`: 输出格式（json/markdown/yaml）
- `--no-progress`: 禁用进度条

**示例**:
```bash
# 分析 Python 和 Go 代码
codesage analyze ./src -l python -l go

# 排除测试文件
codesage analyze ./src -e "*.test.py" -e "*_test.go"

# 输出 JSON 报告
codesage analyze ./src -f json -o report.json
```

### codesage snapshot
**用途**: 管理代码快照

**子命令**:
- `create`: 创建新快照
- `list`: 列出所有快照
- `show <VERSION>`: 显示快照详情
- `cleanup`: 清理过期快照

**示例**:
```bash
# 创建压缩快照
codesage snapshot create --compress

# 查看所有快照
codesage snapshot list

# 查看特定版本
codesage snapshot show v1.0.0

# 清理 30 天前的快照
codesage snapshot cleanup
```

### codesage diff
**用途**: 对比两个快照的差异

**语法**:
```
codesage diff <VERSION1> <VERSION2> [OPTIONS]
```

**选项**:
- `--output, -o`: 输出差异报告路径
- `--format, -f`: 报告格式（json/markdown）

**示例**:
```bash
# 对比两个版本
codesage diff v1.0.0 v1.1.0

# 生成 Markdown 报告
codesage diff v1.0.0 v1.1.0 -f markdown -o diff-report.md
```

### codesage config
**用途**: 管理配置文件

**子命令**:
- `init`: 初始化配置文件
- `validate`: 验证配置文件
- `show`: 显示当前配置
- `set <KEY> <VALUE>`: 修改配置项

**示例**:
```bash
# 交互式初始化
codesage config init --interactive

# 验证配置
codesage config validate

# 修改日志级别
codesage config set cli.log_level debug
```

### codesage report
**用途**: 生成分析报告

**语法**:
```
codesage report <SNAPSHOT_VERSION> [OPTIONS]
```

**选项**:
- `--template, -t`: 模板名称
- `--output, -o`: 输出路径（必需）
- `--include-code`: 包含源代码片段

**示例**:
```bash
# 生成标准报告
codesage report v1.0.0 -o report.md

# 使用自定义模板
codesage report v1.0.0 -t detailed -o detailed-report.md --include-code
```

## 全局选项
- `--config`: 指定配置文件路径
- `--verbose, -v`: 详细输出
- `--no-color`: 禁用彩色输出
- `--version`: 显示版本信息
- `--help, -h`: 显示帮助信息
