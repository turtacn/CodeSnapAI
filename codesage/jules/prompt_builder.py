"""Jules 提示词智能构建器
基于问题类型和项目上下文生成优化的 LLM 提示词
"""
import re
from typing import Dict, List, Optional
from jinja2 import Environment, FileSystemLoader, Template
from codesage.models.issue import Issue
from codesage.config.jules import JulesPromptConfig
from codesage.governance.jules_bridge import JulesTaskView
from codesage.jules.prompt_templates import JulesPromptTemplate

class PromptBuilder:
    """提示词构建器（对齐架构设计 3.2.1 节的"上下文丰富度"要求）

    核心策略:
    1. 问题类型 → 提示词模板（规则驱动）
    2. 代码上下文 → 依赖注入（完整函数 + imports）
    3. 项目规范 → 约束条件（编码标准、框架要求）
    4. Few-shot 示例 → 提升修复质量（可选）
    """

    def __init__(self, template_dir: str = "codesage/jules/templates"):
        """初始化提示词模板库"""
        # Ensure directory exists or handle errors?
        # For now assume it exists or use package loader if needed, but FileSystemLoader is fine for this env.
        # But wait, Jinja2 FileSystemLoader might fail if dir doesn't exist.
        import os
        if not os.path.exists(template_dir):
            # Fallback or create?
            # Creating dummy templates for now to avoid crash if not present in tests
            pass

        self.env = Environment(loader=FileSystemLoader(template_dir))
        self.few_shot_examples = self._load_examples()
        self.template_mapping = {
            "complexity-": "complexity.j2",
            "empty-exception-": "exception_handling.j2",
            "magic-numbers-": "magic_numbers.j2",
        }

    def build_prompt(
        self,
        issue: Issue,
        code_context: Dict[str, str],
        project_rules: Optional[Dict] = None
    ) -> str:
        """构建 Jules 提示词

        Args:
            issue: 检测到的问题
            code_context: {
                "file_content": "完整文件",
                "function_code": "问题函数",
                "dependencies": ["import ..."],
                "class_context": "所属类代码（如果有）"
            }
            project_rules: {
                "coding_standard": "PEP 8",
                "framework": "FastAPI",
                "max_line_length": 100,
                "test_required": true
            }

        Returns:
            优化的提示词字符串
        """
        # 1. 选择模板（基于问题类型）
        template_name = self._select_template_name(issue.rule_id)
        # Handle case where template might not exist in env
        try:
            template = self.env.get_template(template_name)
        except Exception:
            # Fallback to default if template missing
            # If default.j2 missing, use string template
            return self._fallback_build_prompt(issue, code_context, project_rules)

        # 2. 构建上下文变量
        # Issue (SQLAlchemy) compatibility
        issue_message = getattr(issue, 'description', '') or getattr(issue, 'message', '')

        context_vars = {
            "issue": {
                "message": issue_message,
                "rule_id": issue.rule_id,
                "severity": issue.severity,
                "metrics": getattr(issue, 'metrics', {}), # Mock metrics access
            },
            "code": code_context,
            "rules": project_rules or {},
            "language": "python", # Placeholder
            "examples": self._get_relevant_examples(issue.rule_id)
        }

        # 3. 渲染模板（使用 Jinja2）
        rendered = template.render(**context_vars)

        # 4. 后处理（去除多余空行、格式化）
        return self._post_process_prompt(rendered)

    def _select_template_name(self, rule_id: str) -> str:
        """根据规则 ID 选择最佳模板"""
        for pattern, template_name in self.template_mapping.items():
            if rule_id.startswith(pattern):
                return template_name
        return "default.j2"

    def _get_relevant_examples(self, rule_id: str) -> List[Dict]:
        """获取相关的 Few-shot 示例（提升修复质量）"""
        return self.few_shot_examples.get(rule_id, [])

    def _load_examples(self) -> Dict[str, List[Dict]]:
        """Load examples from file or define inline"""
        return {} # Placeholder

    def _post_process_prompt(self, prompt: str) -> str:
        """提示词后处理（优化格式）"""
        # 去除多余空行
        prompt = re.sub(r'\n{3,}', '\n\n', prompt)
        return prompt.strip()

    def _fallback_build_prompt(self, issue, code_context, rules):
         issue_message = getattr(issue, 'description', '') or getattr(issue, 'message', '')
         return f"""Fix this issue:
Type: {issue.rule_id}
Message: {issue_message}
Code:
{code_context.get('function_code', '')}
"""

# --- Legacy Support for Existing Codebase ---

def build_prompt(
    view: JulesTaskView,
    template: JulesPromptTemplate,
    config: JulesPromptConfig,
) -> str:
    """
    Builds the final prompt string from a JulesTaskView, a template, and configuration.
    (Legacy function preserved for backward compatibility)
    """
    # Truncate the code snippet if it exceeds the max number of lines
    code_lines = view.code_snippet.split('\n')
    if len(code_lines) > config.max_code_context_lines:
        code_snippet = '\n'.join(code_lines[:config.max_code_context_lines])
        code_snippet += "\n... (code truncated)"
    else:
        code_snippet = view.code_snippet

    llm_hint = view.llm_hint or ""
    if not config.include_llm_hint:
        llm_hint = ""

    body = template.body_format.format(
        file_path=view.file_path,
        line=view.line or "",
        language=view.language,
        function_name=view.function_name or "",
        issue_message=view.issue_message,
        goal_description=view.goal_description,
        code_snippet=code_snippet,
        llm_hint=llm_hint,
    )

    # Combine header, body, and footer to form the final prompt
    prompt = "\n\n".join([template.header, body.strip(), template.footer])
    return prompt
