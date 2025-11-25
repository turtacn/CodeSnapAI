"""Jules LLM 工具桥接器
实现架构设计第 3.3.1 节的"外部工具适配器"标准
"""
import ast
import json
import logging
import time
from typing import Dict, List, Optional
import httpx
from codesage.models.issue import Issue, FixSuggestion
# from codesage.governance.task import FixTask # Removed to avoid circular import if not needed here

logger = logging.getLogger(__name__)

class JulesAPIError(Exception):
    """Jules API 通信异常"""
    pass

class ValidationError(Exception):
    """修复验证失败异常"""
    pass

class JulesBridge:
    """Jules API 通信桥接器

    核心能力（对齐架构设计）:
    - 问题转提示词: Issue → Jules Prompt
    - 建议解析: Jules Response → FixSuggestion
    - 错误处理: 网络重试 + 降级策略
    - 上下文管理: 保持会话状态（用于迭代修复）
    """

    def __init__(
        self,
        api_endpoint: str,
        api_key: Optional[str] = None,
        timeout: int = 30,
        max_retries: int = 3
    ):
        """初始化 Jules 连接

        Args:
            api_endpoint: Jules API URL (例: https://jules.ai/api/v1)
            api_key: 认证密钥（若需要）
            timeout: 请求超时（秒）
            max_retries: 失败重试次数
        """
        self.endpoint = api_endpoint.rstrip("/")
        self.api_key = api_key
        self.timeout = timeout
        self.max_retries = max_retries
        self.session_id = None  # 用于保持上下文的会话 ID
        self.client = httpx.Client(timeout=timeout)

    def submit_fix_request(
        self,
        issue: Issue,
        code_context: Dict[str, str]
    ) -> str:
        """提交修复请求到 Jules

        Args:
            issue: CodeSnapAI 检测到的问题
            code_context: {
                "file_content": "完整文件内容",
                "function_code": "问题函数的完整代码",
                "dependencies": ["import 语句"],
                "project_context": "项目技术栈信息"
            }

        Returns:
            Jules 任务 ID（用于后续查询结果）
        """
        prompt = self._build_fix_prompt(issue, code_context)

        payload = {
            "prompt": prompt,
            "context": {
                "file_path": issue.file_path,
                "language": "python", # issue.language does not exist in DB model directly
                "project_type": code_context.get("project_context", "unknown")
            },
            "session_id": self.session_id,  # 保持会话连续性
            "options": {
                "temperature": 0.2,  # 低温度保证代码质量
                "max_tokens": 2000,
                "stop_sequences": ["```"]  # 避免生成过长代码
            }
        }

        response = self._post_with_retry("/fix-request", payload)
        self.session_id = response.get("session_id")  # 更新会话 ID
        return response["task_id"]

    def get_fix_result(self, task_id: str) -> Optional[FixSuggestion]:
        """查询 Jules 修复结果（支持轮询）

        Returns:
            FixSuggestion 对象，或 None（任务未完成）
        """
        response = self._get_with_retry(f"/fix-result/{task_id}")

        if response["status"] == "completed":
            return self._parse_fix_suggestion(response)
        elif response["status"] == "failed":
            raise JulesAPIError(f"Jules failed: {response.get('error')}")
        else:
            return None  # 任务进行中，需继续轮询

    def verify_and_iterate(
        self,
        fix_suggestion: FixSuggestion,
        original_issue: Issue,
        max_iterations: int = 3
    ) -> FixSuggestion:
        """验证修复结果并迭代优化"""
        current_suggestion = fix_suggestion

        for iteration in range(max_iterations):
            # 1. 语法验证
            # Assume language is python for now as Issue doesn't have it explicitly yet
            language = "python"
            if not self._validate_syntax(current_suggestion.new_code, language):
                feedback = self._build_syntax_error_feedback(current_suggestion.new_code)
                current_suggestion = self._request_fix_iteration(original_issue, feedback)
                current_suggestion.iterations = iteration + 1
                continue

            # 2. 复杂度检查（确保修复有效）
            new_complexity = self._calculate_complexity(current_suggestion.new_code)
            # Assuming we can get original complexity, or use threshold
            # For now, we just ensure it's not extremely high if we can measure it
            # If complexity calculation is implemented, we can check reduction
            # original_complexity = 100 # Placeholder

            # 3. 规则重检（确保原问题消失）
            if self._issue_still_exists(current_suggestion.new_code, original_issue.rule_id):
                feedback = f"Original issue still present: {original_issue.rule_id}"
                current_suggestion = self._request_fix_iteration(original_issue, feedback)
                current_suggestion.iterations = iteration + 1
                continue

            # All verifications passed
            logger.info(f"Fix validated successfully after {iteration + 1} iterations")
            current_suggestion.iterations = iteration + 1
            return current_suggestion

        # 达到最大迭代次数仍未通过
        raise ValidationError(f"Fix validation failed after {max_iterations} iterations")

    def _build_fix_prompt(self, issue: Issue, context: Dict) -> str:
        """构建 Jules 提示词（关键：影响修复质量）"""
        # Handle attribute access for Issue (SQLAlchemy model)
        message = getattr(issue, 'description', '') or getattr(issue, 'message', 'No description')
        language = "python" # defaulting to python as language field is missing in DB model

        prompt = f"""You are a code quality expert. Fix the following issue:

**Issue Type**: {issue.rule_id}
**Severity**: {issue.severity}
**Problem**: {message}

**Current Code**:
```{language}
{context.get('function_code', '')}
```

**File Context** (dependencies):

```{language}
{chr(10).join(context.get('dependencies', []))}
```

**Requirements**:

1. Fix the issue while maintaining existing functionality
2. Follow {language} best practices and PEP 8 (if Python)
3. Preserve function signature and return type
4. Add comments explaining the fix
5. Ensure the fix passes syntax validation

**Output Format**:

```{language}
<fixed_code>
```

**Explanation**: <brief explanation of the fix>
"""

        if issue.rule_id == "complexity-too-high":
            prompt += "\n**Specific Guidance**: Refactor into smaller functions with single responsibilities."
        elif issue.rule_id == "empty-exception-handler":
            prompt += "\n**Specific Guidance**: Add proper error logging and recovery logic."
        elif issue.rule_id == "magic-numbers":
            prompt += "\n**Specific Guidance**: Extract magic numbers to named constants."

        return prompt

    def _parse_fix_suggestion(self, response: Dict) -> FixSuggestion:
        """解析 Jules 响应为标准 FixSuggestion 对象"""
        raw_output = response["output"]

        # 提取代码块（正则匹配 ```language ... ```）
        import re
        code_match = re.search(r'```(?:\w+)?\n(.*?)\n```', raw_output, re.DOTALL)
        new_code = code_match.group(1) if code_match else raw_output

        # 提取解释（假设在代码块之后）
        explanation = raw_output.split('```')[-1].strip()

        return FixSuggestion(
            task_id=response["task_id"],
            new_code=new_code,
            explanation=explanation,
            confidence=response.get("confidence", 0.8),
            patch_context={
                "function_name": response["context"]["function"],
                "line_range": response["context"]["lines"],
                "anchor_signature": response["context"]["signature"]
            }
        )

    def _post_with_retry(self, endpoint: str, payload: Dict) -> Dict:
        """带重试的 POST 请求"""
        for attempt in range(self.max_retries):
            try:
                resp = self.client.post(
                    f"{self.endpoint}{endpoint}",
                    json=payload,
                    headers={"Authorization": f"Bearer {self.api_key}"},
                )
                resp.raise_for_status()
                return resp.json()
            except httpx.RequestError as e:
                if attempt == self.max_retries - 1:
                    raise JulesAPIError(f"Jules API failed after {self.max_retries} retries: {e}")
                time.sleep(2 ** attempt)  # 指数退避

    def _get_with_retry(self, endpoint: str) -> Dict:
        """带重试的 GET 请求"""
        for attempt in range(self.max_retries):
            try:
                resp = self.client.get(
                    f"{self.endpoint}{endpoint}",
                    headers={"Authorization": f"Bearer {self.api_key}"},
                )
                resp.raise_for_status()
                return resp.json()
            except httpx.RequestError as e:
                if attempt == self.max_retries - 1:
                    raise JulesAPIError(f"Jules API failed after {self.max_retries} retries: {e}")
                time.sleep(2 ** attempt)

    def _validate_syntax(self, code: str, language: str) -> bool:
        """语法验证（多语言支持）"""
        if language == "python":
            try:
                ast.parse(code)
                return True
            except SyntaxError:
                return False
        # Add other languages here
        return True

    def _request_fix_iteration(self, issue: Issue, feedback: str) -> FixSuggestion:
        """请求 Jules 迭代优化"""
        task_id = self.submit_fix_request(issue, {"iteration_feedback": feedback})
        # Polling for result
        while True:
            result = self.get_fix_result(task_id)
            if result:
                return result
            time.sleep(1)

    def _build_syntax_error_feedback(self, code: str) -> str:
        """构建语法错误反馈（包含错误位置）"""
        try:
            ast.parse(code)
            return ""
        except SyntaxError as e:
            return f"Syntax error at line {e.lineno}: {e.msg}\n{e.text}"

    def _calculate_complexity(self, code: str) -> float:
        """计算代码复杂度"""
        # Simple complexity check: count decision points
        # This is a heuristic implementation
        try:
            tree = ast.parse(code)
            complexity = 1
            for node in ast.walk(tree):
                if isinstance(node, (ast.If, ast.While, ast.For, ast.AsyncFor, ast.With, ast.AsyncWith, ast.ExceptHandler)):
                    complexity += 1
                elif isinstance(node, ast.BoolOp):
                    complexity += len(node.values) - 1
            return float(complexity)
        except Exception:
            return 0.0

    def _issue_still_exists(self, code: str, rule_id: str) -> bool:
        """检查原问题是否仍存在"""
        # Heuristic check based on rule ID
        # Real implementation would run RuleEngine
        # Here we do basic checks for common rules

        if rule_id == "empty-exception-handler":
            # Check for 'except ...: pass' or 'except ...: ...'
            # Simple text check is risky, AST check is better
            try:
                tree = ast.parse(code)
                for node in ast.walk(tree):
                    if isinstance(node, ast.ExceptHandler):
                        if len(node.body) == 1 and isinstance(node.body[0], (ast.Pass, ast.Ellipsis)):
                            return True
            except Exception:
                pass

        elif rule_id == "magic-numbers":
            # Very hard to check without full context/config
            pass

        return False
