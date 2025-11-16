from typing import List
from abc import ABC, abstractmethod

from codesage.analyzers.ast_models import FileAST
from codesage.analyzers.semantic.models import DetectedPattern, CodeLocation
from codesage.analyzers.semantic.base_analyzer import AnalysisContext

class PatternRule(ABC):
    @property
    @abstractmethod
    def pattern_type(self) -> str:
        ...

    @abstractmethod
    def match(self, file_ast: FileAST, context: AnalysisContext) -> List[DetectedPattern]:
        ...

class GodClassRule(PatternRule):
    @property
    def pattern_type(self) -> str:
        return "god_class"

    def match(self, file_ast: FileAST, context: AnalysisContext) -> List[DetectedPattern]:
        patterns = []
        threshold = context.config.get("patterns", {}).get("god_class_threshold", 20)
        for class_node in file_ast.classes:
            if len(class_node.methods) > threshold:
                patterns.append(DetectedPattern(
                    pattern_type=self.pattern_type,
                    confidence=1.0,
                    location=CodeLocation(file=file_ast.path, start_line=class_node.start_line, end_line=class_node.end_line),
                    description=f"Class {class_node.name} has too many methods ({len(class_node.methods)})."
                ))
        return patterns

class LongFunctionRule(PatternRule):
    @property
    def pattern_type(self) -> str:
        return "long_function"

    def match(self, file_ast: FileAST, context: AnalysisContext) -> List[DetectedPattern]:
        patterns = []
        threshold = context.config.get("patterns", {}).get("long_function_threshold", 50)
        all_functions = file_ast.functions
        for class_node in file_ast.classes:
            all_functions.extend(class_node.methods)

        for func in all_functions:
            line_count = func.end_line - func.start_line
            if line_count > threshold:
                patterns.append(DetectedPattern(
                    pattern_type=self.pattern_type,
                    confidence=1.0,
                    location=CodeLocation(file=file_ast.path, start_line=func.start_line, end_line=func.end_line),
                    description=f"Function {func.name} is too long ({line_count} lines)."
                ))
        return patterns

class FactoryRule(PatternRule):
    @property
    def pattern_type(self) -> str:
        return "factory"

    def match(self, file_ast: FileAST, context: AnalysisContext) -> List[DetectedPattern]:
        patterns = []
        if ".go" in file_ast.path:
            for func in file_ast.functions:
                if func.name.startswith("New"):
                    patterns.append(DetectedPattern(
                        pattern_type=self.pattern_type,
                        confidence=0.8,
                        location=CodeLocation(file=file_ast.path, start_line=func.start_line, end_line=func.end_line),
                        description=f"Function {func.name} appears to be a factory."
                    ))
        return patterns
