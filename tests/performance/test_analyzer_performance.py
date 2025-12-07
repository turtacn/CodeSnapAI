"""
Performance test suite for analyzers
"""
import pytest
import time
import tracemalloc
from codesage.analyzers.parser_factory import create_parser


class TestAnalyzerPerformance:
    """Performance tests for all analyzers"""
    
    def _generate_python_code(self, lines: int) -> str:
        """Generate Python code with specified number of lines"""
        code_lines = [
            "import os",
            "import sys",
            "from typing import List, Dict, Optional",
            ""
        ]
        
        for i in range(lines // 20):  # Approximately 20 lines per function
            code_lines.extend([
                f"def function_{i}(param1: str, param2: int, param3: Optional[Dict] = None) -> List[str]:",
                f'    """Function {i} docstring"""',
                f"    results = []",
                f"    if param1 and param2 > 0:",
                f"        for j in range(param2):",
                f"            if j % 2 == 0:",
                f"                result = f'{{param1}}_{{j}}'",
                f"                if param3:",
                f"                    result += str(param3.get('key', ''))",
                f"                results.append(result)",
                f"            else:",
                f"                results.append(f'odd_{{j}}')",
                f"    elif param1:",
                f"        return [param1]",
                f"    else:",
                f"        return []",
                f"    return results",
                ""
            ])
        
        return '\n'.join(code_lines)
    
    @pytest.mark.benchmark
    def test_python_parsing_speed_1000_loc(self, benchmark):
        """Test Python parsing speed for 1000 lines of code"""
        code = self._generate_python_code(1000)
        
        def parse_python():
            parser = create_parser('python')
            parser.parse(code)
            functions = parser.extract_functions()
            classes = parser.extract_classes()
            imports = parser.extract_imports()
            return len(functions), len(classes), len(imports)
        
        result = benchmark(parse_python)
        
        # Verify parsing worked
        func_count, class_count, import_count = result
        assert func_count > 0
        
        # Performance requirement: < 500ms for 1000 LOC
        assert benchmark.stats.mean < 0.5
    
    def test_memory_usage_large_python_file(self):
        """Test memory usage for large Python file"""
        # Generate 5,000 lines of Python code (reduced for CI)
        code = self._generate_python_code(5000)
        
        tracemalloc.start()
        
        parser = create_parser('python')
        parser.parse(code)
        functions = parser.extract_functions()
        classes = parser.extract_classes()
        
        current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        
        # Verify parsing worked
        assert len(functions) > 0
        
        # Memory requirement: < 200MB peak usage
        peak_mb = peak / 1024 / 1024
        assert peak_mb < 200, f"Peak memory usage: {peak_mb:.2f}MB"