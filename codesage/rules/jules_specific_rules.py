"""Jules LLM 代码生成的特定反模式检测
基于实际使用经验沉淀的规则集
"""
import ast
import re
from typing import Optional, List, Any
from codesage.rules.base import BaseRule, RuleContext
from codesage.snapshot.models import Issue, FileSnapshot

# Adapter class to bridge old Rule interface if needed or use BaseRule
# The existing code seems to use BaseRule.
# My implementations used a simpler interface: check(self, snapshot: FileSnapshot)
# I need to adapt them to match `check(self, ctx: RuleContext)`

class JulesRule(BaseRule):
    """Base class for Jules-specific rules simplifying access"""
    rule_id: str = "jules-base"
    description: str = "Base Jules Rule"

    # We need to define these as fields for Pydantic if BaseRule inherits from BaseModel?
    # Checking BaseRule in base.py: inherits from ABC. Not Pydantic model.
    # But it has type annotations.

    # Actually BaseRule is abstract.
    # Let's override check.

    def check(self, ctx: RuleContext) -> List[Issue]:
        return self.check_file(ctx.file)

    def check_file(self, snapshot: FileSnapshot) -> List[Issue]:
        raise NotImplementedError

class IncompleteErrorHandling(JulesRule):
    """检测 LLM 生成代码中常见的"半成品异常处理"
    """
    rule_id = "jules-001"
    description = "Empty exception handler (common LLM artifact)"
    severity = "HIGH" # Not part of BaseRule interface directly but used in logic

    def check_file(self, snapshot: FileSnapshot) -> List[Issue]:
        issues = []
        if snapshot.language != "python":
            return issues

        try:
            tree = ast.parse(snapshot.content)
            for node in ast.walk(tree):
                if isinstance(node, ast.ExceptHandler):
                    if len(node.body) == 1:
                        child = node.body[0]
                        if isinstance(child, (ast.Pass, ast.Ellipsis)):
                            issues.append(Issue(
                                rule_id=self.rule_id,
                                severity="error", # Mapped from HIGH
                                message=self.description,
                                location={"file_path": snapshot.path, "line": node.lineno},
                                symbol=None,
                                tags=["jules-pattern"]
                            ))
        except Exception:
            pass
        return issues

class MagicNumbersInConfig(JulesRule):
    """检测硬编码的配置值（LLM 常忘记参数化）
    """
    rule_id = "jules-002"
    description = "Hardcoded configuration value"

    def check_file(self, snapshot: FileSnapshot) -> List[Issue]:
        issues = []
        if snapshot.language != "python":
            return issues

        try:
            tree = ast.parse(snapshot.content)
            for node in ast.walk(tree):
                if isinstance(node, ast.Assign):
                    for target in node.targets:
                        if isinstance(target, ast.Name):
                            name = target.id.lower()
                            if any(k in name for k in ['timeout', 'retries', 'limit', 'threshold']):
                                if isinstance(node.value, ast.Constant) and isinstance(node.value.value, (int, float)):
                                    issues.append(Issue(
                                        rule_id=self.rule_id,
                                        severity="warning",
                                        message=f"Hardcoded configuration value '{target.id}'",
                                        location={"file_path": snapshot.path, "line": node.lineno},
                                        symbol=target.id,
                                        tags=["jules-pattern"]
                                    ))
        except Exception:
            pass
        return issues

class InconsistentNamingConvention(JulesRule):
    """检测 LLM 生成代码的命名风格不一致
    """
    rule_id = "jules-003"
    description = "Mixed naming conventions detected"

    def check_file(self, snapshot: FileSnapshot) -> List[Issue]:
        issues = []
        if snapshot.language != "python":
            return issues

        try:
            tree = ast.parse(snapshot.content)
            snake_case_count = 0
            camel_case_count = 0

            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    name = node.name
                    if not name.startswith('_'):
                        if name.islower() and '_' in name:
                            snake_case_count += 1
                        elif name != name.lower() and '_' not in name:
                            camel_case_count += 1

            if snake_case_count > 0 and camel_case_count > 0:
                issues.append(Issue(
                    rule_id=self.rule_id,
                    severity="info",
                    message=f"Mixed naming conventions detected (snake_case: {snake_case_count}, camelCase: {camel_case_count})",
                    location={"file_path": snapshot.path, "line": 1},
                    symbol=None,
                    tags=["jules-pattern"]
                ))
        except Exception:
            pass
        return issues

class LongFunctionRule(JulesRule):
    """检测 LLM 生成的过长函数"""
    rule_id = "jules-004"
    description = "Function is too long"

    def check_file(self, snapshot: FileSnapshot) -> List[Issue]:
        issues = []
        if snapshot.language != "python": return issues
        try:
            tree = ast.parse(snapshot.content)
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    length = node.end_lineno - node.lineno
                    if length > 50:
                        issues.append(Issue(
                            rule_id=self.rule_id,
                            severity="warning",
                            message=f"Function '{node.name}' is too long ({length} lines)",
                            location={"file_path": snapshot.path, "line": node.lineno},
                            symbol=node.name,
                            tags=["jules-pattern"]
                        ))
        except Exception: pass
        return issues

class TODOLeftoverRule(JulesRule):
    """检测 LLM 留下的 TODO 注释"""
    rule_id = "jules-005"
    description = "Found TODO comment"

    def check_file(self, snapshot: FileSnapshot) -> List[Issue]:
        issues = []
        if not snapshot.content: return issues
        lines = snapshot.content.splitlines()
        for i, line in enumerate(lines):
            if "TODO" in line:
                issues.append(Issue(
                    rule_id=self.rule_id,
                    severity="info",
                    message="Found TODO comment",
                    location={"file_path": snapshot.path, "line": i+1},
                    symbol=None,
                    tags=["jules-pattern"]
                ))
        return issues

class HardcodedPathRule(JulesRule):
    """检测硬编码的文件路径"""
    rule_id = "jules-006"
    description = "Possible hardcoded path detected"

    def check_file(self, snapshot: FileSnapshot) -> List[Issue]:
        issues = []
        if snapshot.language != "python": return issues
        try:
            tree = ast.parse(snapshot.content)
            for node in ast.walk(tree):
                if isinstance(node, ast.Constant) and isinstance(node.value, str):
                    val = node.value
                    if (val.startswith("/") or "C:\\" in val) and len(val) > 3:
                        issues.append(Issue(
                            rule_id=self.rule_id,
                            severity="warning",
                            message=f"Possible hardcoded path detected: '{val}'",
                            location={"file_path": snapshot.path, "line": node.lineno},
                            symbol=None,
                            tags=["jules-pattern"]
                        ))
        except Exception: pass
        return issues

class PrintStatementRule(JulesRule):
    """检测遗留的 print 调试语句"""
    rule_id = "jules-007"
    description = "Use of print() detected"

    def check_file(self, snapshot: FileSnapshot) -> List[Issue]:
        issues = []
        if snapshot.language != "python": return issues
        try:
            tree = ast.parse(snapshot.content)
            for node in ast.walk(tree):
                if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "print":
                    issues.append(Issue(
                        rule_id=self.rule_id,
                        severity="info",
                        message="Use of print() detected",
                        location={"file_path": snapshot.path, "line": node.lineno},
                        symbol="print",
                        tags=["jules-pattern"]
                    ))
        except Exception: pass
        return issues

class BroadExceptionRule(JulesRule):
    """检测捕获所有异常 (Exception) 而不记录"""
    rule_id = "jules-008"
    description = "Broad exception caught without logging"

    def check_file(self, snapshot: FileSnapshot) -> List[Issue]:
        issues = []
        if snapshot.language != "python": return issues
        try:
            tree = ast.parse(snapshot.content)
            for node in ast.walk(tree):
                if isinstance(node, ast.ExceptHandler):
                     if node.type is None or (isinstance(node.type, ast.Name) and node.type.id == "Exception"):
                         # Check if logged or re-raised
                         has_logging = False
                         for child in node.body:
                             if isinstance(child, ast.Raise): has_logging = True
                             if isinstance(child, ast.Call) and hasattr(child.func, 'attr') and child.func.attr in ['error', 'exception']: has_logging = True

                         if not has_logging:
                             issues.append(Issue(
                                 rule_id=self.rule_id,
                                 severity="warning",
                                 message="Broad exception caught without logging or re-raising",
                                 location={"file_path": snapshot.path, "line": node.lineno},
                                 symbol=None,
                                 tags=["jules-pattern"]
                             ))
        except Exception: pass
        return issues

class PlaceholderFunctionRule(JulesRule):
    """检测占位符函数 (pass)"""
    rule_id = "jules-009"
    description = "Placeholder function detected"

    def check_file(self, snapshot: FileSnapshot) -> List[Issue]:
        issues = []
        if snapshot.language != "python": return issues
        try:
            tree = ast.parse(snapshot.content)
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    if len(node.body) == 1 and isinstance(node.body[0], ast.Pass):
                         issues.append(Issue(
                            rule_id=self.rule_id,
                            severity="info",
                            message=f"Placeholder function '{node.name}'",
                            location={"file_path": snapshot.path, "line": node.lineno},
                            symbol=node.name,
                            tags=["jules-pattern"]
                        ))
        except Exception: pass
        return issues

class MissingDocstringRule(JulesRule):
    """检测缺少文档字符串的函数"""
    rule_id = "jules-010"
    description = "Missing docstring"

    def check_file(self, snapshot: FileSnapshot) -> List[Issue]:
        issues = []
        if snapshot.language != "python": return issues
        try:
            tree = ast.parse(snapshot.content)
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    if not ast.get_docstring(node) and not node.name.startswith('_'):
                        issues.append(Issue(
                            rule_id=self.rule_id,
                            severity="info",
                            message=f"Missing docstring for '{node.name}'",
                            location={"file_path": snapshot.path, "line": node.lineno},
                            symbol=node.name,
                            tags=["jules-pattern"]
                        ))
        except Exception: pass
        return issues

JULES_RULESET = [
    IncompleteErrorHandling(),
    MagicNumbersInConfig(),
    InconsistentNamingConvention(),
    LongFunctionRule(),
    TODOLeftoverRule(),
    HardcodedPathRule(),
    PrintStatementRule(),
    BroadExceptionRule(),
    PlaceholderFunctionRule(),
    MissingDocstringRule()
]
