from typing import List, Dict, Any
from codesage.core.interfaces import Plugin, Rule, CodeIssue

class NoPrintRule(Rule):
    id = "custom-no-print"
    description = "Avoid using print() in production code."
    severity = "medium"

    def check(self, file_path: str, content: str, context: Dict[str, Any]) -> List[CodeIssue]:
        issues = []
        lines = content.split('\n')
        for i, line in enumerate(lines):
            if "print(" in line and not line.strip().startswith("#"):
                issues.append(CodeIssue(
                    file_path=file_path,
                    line_number=i + 1,
                    severity=self.severity,
                    description=self.description,
                    rule_id=self.id
                ))
        return issues

class MyCustomPlugin(Plugin):
    def register(self, engine):
        engine.register_rule(NoPrintRule())
