<div align="center">
  <img src="logo.png" alt="CodeSnapAI Logo" width="200" height="200">
  
  # CodeSnapAI
  
  **AI驱动的语义代码分析与智能治理平台**
  
  [![构建状态](https://img.shields.io/badge/build-passing-brightgreen)](https://github.com/turtacn/CodeSnapAI)
  [![许可证](https://img.shields.io/badge/license-Apache%202.0-blue.svg)](LICENSE)
  [![Python版本](https://img.shields.io/badge/python-3.10%2B-blue)](https://www.python.org/)
  [![覆盖率](https://img.shields.io/badge/coverage-95%25-green)](https://github.com/turtacn/CodeSnapAI)
  [![欢迎PR](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](CONTRIBUTING.md)
  
  [English](README.md) | [简体中文](README-zh.md)
</div>

---

## 🎯 核心使命

CodeSnapAI 致力于解决现代软件工程中的关键难题："**上下文爆炸与信息丢失**"的悖论。我们将海量代码库压缩为超紧凑的语义快照，同时保留95%以上的调试关键信息，使AI辅助开发达到前所未有的规模。

**核心创新**：将5MB+的代码库转化为<200KB的语义表示，让大语言模型真正理解并采取行动。

---

## 💡 为什么选择 CodeSnapAI？

### 行业痛点分析

现代软件开发面临**三大关键瓶颈**：

| 挑战 | 现状 | CodeSnapAI解决方案 |
|------|------|-------------------|
| **上下文过载** | 大型代码库包含数百万个细节，压垮AI调试器和开发者 | 基于风险权重的智能语义压缩 |
| **语义丢失** | 传统代码摘要丢失关键依赖关系和错误模式 | 多维度语义标签系统保持架构完整性 |
| **治理碎片化** | 复杂度检测工具（SonarQube、Codacy）报告问题但需要人工修复 | 自动化端到端工作流：扫描 → AI生成补丁 → 验证 → 部署 |
| **多语言混乱** | 每种语言需要独立的工具链和分析框架 | 跨Go、Java、C/C++、Rust、Python的统一语义抽象层 |

### 竞争优势

🚀 **20:1压缩比** - 业界领先的语义快照技术  
🎯 **95%+信息保留率** - 保留所有调试关键关系  
🔄 **闭环自动化** - 从问题检测到验证补丁部署  
🌐 **通用语言支持** - 跨5+主流语言的统一分析  
⚡ **30秒内分析** - 处理10万行代码项目仅需30秒  
🔓 **开源可扩展** - 支持自定义规则和语言的插件架构

---

## ✨ 核心特性

### 1. **多语言语义分析器**
- **统一AST解析**：基于tree-sitter支持Go、Java、C/C++、Rust、Python
- **深度语义提取**：
  - 函数签名、调用图、依赖树
  - 复杂度指标（圈复杂度、认知复杂度、嵌套深度）
  - 错误处理模式（panic/error包装/异常）
  - 并发原语（goroutine、async/await、channel）
  - 数据库/网络操作标记
- **增量分析**：基于文件级哈希的高效变更检测

### 2. **智能快照生成器**
- **高级压缩策略**：
  - 包级聚合与代表性采样
  - 关键路径提取（高调用频次函数优先）
  - 基于功能标签的语义聚类
  - 风险加权剪枝（高风险模块完整保留）
- **多种输出格式**：YAML（人类可读）、JSON（API）、二进制（性能）
- **丰富元数据**：项目结构、依赖图、风险热图、Git上下文

### 3. **风险评分引擎**
- **多维度风险模型**：
  - 复杂度评分（McCabe + 认知复杂度加权）
  - 错误模式分析（不安全操作、缺失处理器）
  - 关键路径测试覆盖率惩罚
  - 传递性依赖漏洞传播
  - Git历史变更频率（不稳定性指标）
- **可配置阈值**：按项目类型自定义评分规则
- **可操作报告**：根因分析与下钻能力

### 4. **AI治理编排器**
- **自动化问题检测**：
  - 圈复杂度 > 10（可配置）
  - 认知复杂度 > 15
  - 嵌套深度 > 4
  - 函数长度 > 50行
  - 参数数量 > 5
  - 代码重复率 > 3%
- **LLM驱动重构**：
  - 上下文丰富的提示生成
  - 结构化JSON输出验证
  - 多轮对话支持
- **补丁管理流水线**：
  - 通过语言解析器进行语法验证
  - 自动化测试执行（补丁前后）
  - 基于Git的回滚机制
  - 可选审批工作流

### 5. **交互式调试助手**
- **自然语言查询**：
  - "为什么TestUserLogin失败？" → 完整调用链定位
  - "显示高风险模块" → 带理由的排序列表
  - "解释ProcessPayment函数" → 语义摘要 + 依赖关系
- **调试器集成**：兼容pdb、gdb、lldb、delve
- **实时导航**：跨代码库的语义搜索

---

## 🚀 快速开始

### 前置要求
- Python 3.10或更高版本
- Git（用于代码仓库分析功能）

### 安装

#### 通过pip安装（推荐）
```bash
pip install codesage
````

#### 从源码安装

```bash
git clone https://github.com/turtacn/CodeSnapAI.git
cd CodeSnapAI
pip install -e .
```

### 快速入门

#### 1. 生成语义快照

```bash
# 分析Go微服务项目
codesage snapshot ./my-go-service -o snapshot.yaml

# 输出：snapshot.yaml（压缩的语义表示）
```

#### 2. 分析架构

```bash
codesage analyze snapshot.yaml

# 输出示例：
# 项目：my-go-service (Go 1.21)
# 总函数数：342
# 高风险模块：12（详见下方）
# 复杂度热点：
#   - handlers/auth.go::ValidateToken（圈复杂度：18，认知复杂度：24）
#   - services/payment.go::ProcessRefund（圈复杂度：15，认知复杂度：21）
```

#### 3. 调试测试失败

```bash
codesage debug snapshot.yaml TestUserRegistration

# 输出：
# 测试失败定位：
# 根因：handlers/user.go::RegisterUser，第45行
# 调用链：RegisterUser → ValidateEmail → CheckDuplicates
# 风险因素：数据库超时缺少错误处理（第52行）
# 修复建议：使用context.WithTimeout包装db.Query
```

#### 4. 复杂度治理工作流

```bash
# 扫描复杂度违规
codesage scan ./my-go-service --threshold cyclomatic=10 cognitive=15

# 使用LLM自动生成重构
codesage govern scan_results.json --llm claude-3-5-sonnet --apply

# 输出：
# 检测到8个违规
# 生成8个重构补丁
# 验证：7/8通过测试（1个需要人工审核）
# 已应用补丁至：handlers/auth.go, services/payment.go, ...
```

---

## 📊 使用示例

### 示例1：CI/CD集成

```yaml
# .github/workflows/code-quality.yml
name: 代码质量门禁
on: [pull_request]

jobs:
  complexity-check:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: 安装CodeSnapAI
        run: pip install codesage
      
      - name: 复杂度分析
        run: |
          codesage scan . --threshold cyclomatic=12 --output report.json
          codesage gate report.json --max-violations 5
```

### 示例2：Python库使用

```python
from codesage import SemanticAnalyzer, SnapshotGenerator, RiskScorer

# 初始化分析器
analyzer = SemanticAnalyzer(language='go')
analysis = analyzer.analyze_directory('./my-service')

# 生成快照
generator = SnapshotGenerator(compression_ratio=20)
snapshot = generator.create(analysis)
snapshot.save('snapshot.yaml')

# 风险评分
scorer = RiskScorer()
risks = scorer.score(analysis)
print(f"高风险模块数：{len(risks.high_risk)}")

for module in risks.high_risk:
    print(f"  {module.path}: {module.score}/100")
    print(f"    原因：{', '.join(module.risk_factors)}")
```

### 示例3：自定义语言插件

```python
from codesage.plugins import LanguagePlugin

class KotlinPlugin(LanguagePlugin):
    def get_tree_sitter_grammar(self):
        return 'tree-sitter-kotlin'
    
    def extract_semantic_tags(self, node):
        # 自定义语义提取逻辑
        if node.type == 'coroutine_declaration':
            return ['async', 'concurrency']
        return []

# 注册插件
from codesage import PluginRegistry
PluginRegistry.register('kotlin', KotlinPlugin())
```

---

## 🎬 演示场景

### 场景1：实时复杂度监控

```bash
# 监视模式持续分析
codesage watch ./src --alert-on complexity>15

# 终端输出（带颜色编码警报）：
# ⚠️  警告：handlers/auth.go::ValidateToken
#    认知复杂度增加：12 → 17 (+5)
#    建议：将验证逻辑提取到独立函数
```

**GIF演示**：`docs/demos/complexity-monitoring.gif`

### 场景2：AI辅助重构

```bash
# 交互式重构会话
codesage refactor ./services/payment.go --interactive

# LLM对话：
# 🤖 我发现了3个复杂度问题。让我们从ProcessRefund开始：
#    当前圈复杂度：18
#    建议方法：提取重试逻辑和错误处理
#    
# 👤 先关注重试逻辑
# 🤖 生成补丁：[显示差异]
#    测试：✅ 所有12个测试通过
#    应用此更改？(y/n)
```

**GIF演示**：`docs/demos/interactive-refactoring.gif`

### 场景3：多仓库仪表板

```bash
# 分析多个项目
codesage dashboard --repos "service-a,service-b,service-c" --port 8080

# 打开Web界面显示：
# - 跨项目复杂度趋势
# - 共享高风险模式
# - 依赖漏洞热图
```

**GIF演示**：`docs/demos/multi-repo-dashboard.gif`

---

## 🛠️ 配置

### 项目配置文件（`.codesage.yaml`）

```yaml
version: "1.0"

# 语言设置
languages:
  - go
  - python

# 压缩设置
snapshot:
  compression_ratio: 20
  preserve_patterns:
    - ".*_test.go$"  # 保留所有测试文件
    - "main.go$"     # 保留入口文件

# 复杂度阈值
thresholds:
  cyclomatic_complexity: 10
  cognitive_complexity: 15
  nesting_depth: 4
  function_length: 50
  parameter_count: 5
  duplication_rate: 0.03

# 风险评分权重
risk_scoring:
  complexity_weight: 0.3
  error_pattern_weight: 0.25
  test_coverage_weight: 0.2
  dependency_weight: 0.15
  change_frequency_weight: 0.1

# LLM集成
llm:
  provider: anthropic  # 或openai、local
  model: claude-3-5-sonnet-20241022
  temperature: 0.2
  max_tokens: 4096
```

---

## 📚 文档

* [架构概览](docs/architecture.md) - 系统设计与组件详情
* [API参考](docs/api-reference.md) - Python库文档
* [插件开发](docs/plugin-development.md) - 创建自定义语言分析器
* [性能调优](docs/performance.md) - 大型代码库优化策略
* [治理工作流](docs/governance-workflows.md) - 自动化重构最佳实践

---

## 🤝 贡献

我们欢迎社区贡献！CodeSnapAI基于"**更好的代码分析工具惠及所有人**"的原则构建。

### 如何贡献

1. **Fork仓库**

   ```bash
   git clone https://github.com/turtacn/CodeSnapAI.git
   cd CodeSnapAI
   ```

2. **创建特性分支**

   ```bash
   git checkout -b feature/your-amazing-feature
   ```

3. **进行更改**
   - 遵循我们的[代码风格指南](CONTRIBUTING.md#code-style)
   - 为新功能添加测试
   - 更新文档

4. **运行测试**
   ```bash
   pytest tests/ --cov=codesage

5. **提交拉取请求**

   * 使用我们的[PR模板](.github/PULL_REQUEST_TEMPLATE.md)
   * 链接相关issue

### 贡献领域

* 🌐 **语言支持**：添加新语言解析器（Scala、Swift等）
* 📊 **指标**：实现新的复杂度或质量指标
* 🤖 **LLM集成**：添加对新AI模型的支持
* 📝 **文档**：改进指南和示例
* 🐛 **Bug修复**：帮助我们消灭bug

详细指南请参阅[CONTRIBUTING.md](CONTRIBUTING.md)。

---

## 📄 许可证

CodeSnapAI基于[Apache License 2.0](LICENSE)发布。

```
Copyright 2024 CodeSnapAI Contributors

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
```

---

## 🙏 致谢

CodeSnapAI基于以下优秀项目构建：

* [tree-sitter](https://tree-sitter.github.io/) - 增量解析系统
* [Anthropic Claude](https://www.anthropic.com/) - 先进的语言模型能力
* [FastAPI](https://fastapi.tiangolo.com/) - 现代API框架

特别感谢所有[贡献者](https://github.com/turtacn/CodeSnapAI/graphs/contributors)让这个项目成为可能。

---

## 📞 支持与社区

* 💬 **讨论区**：[GitHub Discussions](https://github.com/turtacn/CodeSnapAI/discussions)
* 🐛 **Bug报告**：[Issue追踪器](https://github.com/turtacn/CodeSnapAI/issues)
* 📧 **邮箱**：[codesnapai@example.com](mailto:codesnapai@example.com)
* 🐦 **Twitter**：[@CodeSnapAI](https://twitter.com/CodeSnapAI)

---

<div align="center">
  <sub>用❤️由开源社区构建</sub>
</div>
```