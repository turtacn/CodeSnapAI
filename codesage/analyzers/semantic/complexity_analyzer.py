from typing import List, Dict, Tuple
from collections import defaultdict
import math

from codesage.analyzers.ast_models import FileAST, FunctionNode, ASTNode
from codesage.analyzers.semantic.base_analyzer import SemanticAnalyzer, AnalysisContext
from codesage.analyzers.semantic.models import ComplexityMetrics

class ComplexityAnalyzer(SemanticAnalyzer[ComplexityMetrics]):
    def analyze(self, file_ast: FileAST, context: AnalysisContext) -> ComplexityMetrics:
        all_functions = file_ast.functions
        for class_node in file_ast.classes:
            all_functions.extend(class_node.methods)

        for func in all_functions:
            func.cognitive_complexity = self._calculate_cognitive(func)

        metrics = self._aggregate_file_metrics(all_functions, file_ast)
        halstead_metrics = self._calculate_halstead(file_ast)
        metrics.halstead_volume = halstead_metrics.get("volume", 0.0)
        return metrics

    def _calculate_cyclomatic(self, function_node: FunctionNode) -> int:
        return function_node.cyclomatic_complexity

    def _calculate_cognitive(self, function_node: FunctionNode) -> int:
        return self._cognitive_complexity_rek(function_node)

    def _cognitive_complexity_rek(self, node: ASTNode, nesting_level: int = 0) -> int:
        if node is None:
            return 0

        increment = 0
        if node.node_type in ['if_statement', 'for_statement', 'while_statement', 'switch_statement', 'catch_clause']:
            increment = 1 + nesting_level
        elif node.node_type in ['binary_expression', 'logical_expression'] and node.value in ['&&', '||']:
            increment = 1

        child_complexity = sum(self._cognitive_complexity_rek(child, nesting_level + (1 if node.node_type in ['if_statement', 'for_statement', 'while_statement', 'switch_statement', 'catch_clause'] else 0)) for child in node.children)
        return increment + child_complexity

    def _calculate_halstead(self, file_ast: FileAST) -> Dict[str, float]:
        operators = set()
        operands = set()
        n1, n2 = 0, 0

        def traverse(node: ASTNode):
            nonlocal n1, n2
            if node is None:
                return

            # Simplified classification of operators and operands
            if 'expression' in node.node_type or 'statement' in node.node_type:
                operators.add(node.node_type)
                n1 += 1
            elif 'identifier' in node.node_type or 'literal' in node.node_type:
                operands.add(node.value)
                n2 += 1

            for child in node.children:
                traverse(child)

        traverse(file_ast.tree)

        N1 = len(operators)
        N2 = len(operands)

        if N1 == 0 or N2 == 0:
            return {}

        program_length = N1 + N2
        vocabulary = n1 + n2
        volume = program_length * math.log2(vocabulary) if vocabulary > 0 else 0
        difficulty = (n1 / 2) * (N2 / n2) if n2 > 0 else 0

        return {
            "length": program_length,
            "vocabulary": vocabulary,
            "volume": volume,
            "difficulty": difficulty,
        }

    def _aggregate_file_metrics(self, functions: List[FunctionNode], file_ast: FileAST) -> ComplexityMetrics:
        if not functions:
            return ComplexityMetrics(
                cyclomatic_complexity=0, cognitive_complexity=0, halstead_volume=0.0,
                max_function_complexity=0, avg_function_complexity=0.0
            )

        total_cyclo = sum(f.cyclomatic_complexity for f in functions)
        total_cog = sum(f.cognitive_complexity for f in functions)

        max_cyclo = max(f.cyclomatic_complexity for f in functions)
        avg_cyclo = total_cyclo / len(functions)

        return ComplexityMetrics(
            cyclomatic_complexity=total_cyclo,
            cognitive_complexity=total_cog,
            halstead_volume=0.0,  # This will be filled in later
            max_function_complexity=max_cyclo,
            avg_function_complexity=avg_cyclo,
        )
