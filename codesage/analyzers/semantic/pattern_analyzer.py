from typing import List

from codesage.analyzers.ast_models import FileAST
from codesage.analyzers.semantic.base_analyzer import SemanticAnalyzer, AnalysisContext
from codesage.analyzers.semantic.models import DetectedPattern
from codesage.analyzers.semantic.rules.pattern_rules import PatternRule, GodClassRule, LongFunctionRule, FactoryRule

class PatternAnalyzer(SemanticAnalyzer[List[DetectedPattern]]):
    def __init__(self):
        self._rules: List[PatternRule] = [
            GodClassRule(),
            LongFunctionRule(),
            FactoryRule(),
        ]

    def analyze(self, file_ast: FileAST, context: AnalysisContext) -> List[DetectedPattern]:
        patterns = []
        for rule in self._rules:
            patterns.extend(rule.match(file_ast, context))
        return patterns
