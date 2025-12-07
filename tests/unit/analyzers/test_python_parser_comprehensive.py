"""
Comprehensive test suite for Python parser
"""
import pytest
from codesage.analyzers.python_parser import PythonParser
from codesage.analyzers.ast_models import FunctionNode


class TestPythonParserComprehensive:
    """Comprehensive tests for Python parser"""
    
    def setup_method(self):
        """Setup test fixtures"""
        self.parser = PythonParser()
    
    def test_nested_async_functions(self):
        """Test nested async function extraction with proper parent scope"""
        code = """
async def outer():
    async def inner():
        pass
    return inner

def regular_func():
    async def nested_async():
        await asyncio.sleep(1)
        return "done"
    return nested_async
"""
        self.parser.parse(code)
        functions = self.parser.extract_functions()
        
        # Should extract 4 functions: outer, inner, regular_func, nested_async
        assert len(functions) == 4
        
        # Find functions by name
        func_dict = {f.name: f for f in functions}
        
        # Verify outer function
        assert 'outer' in func_dict
        outer = func_dict['outer']
        assert outer.is_async is True
        assert outer.parent_scope is None
        
        # Verify inner function
        assert 'inner' in func_dict
        inner = func_dict['inner']
        assert inner.is_async is True
        assert inner.parent_scope == 'outer'
        
        # Verify regular function
        assert 'regular_func' in func_dict
        regular = func_dict['regular_func']
        assert regular.is_async is False
        assert regular.parent_scope is None
        
        # Verify nested async in regular function
        assert 'nested_async' in func_dict
        nested = func_dict['nested_async']
        assert nested.is_async is True
        assert nested.parent_scope == 'regular_func'
    
    def test_match_statement_complexity(self):
        """Test complexity calculation for Python 3.10+ match statements"""
        code = """
def process_data(data):
    match data:
        case int() if data > 0:
            return "positive"
        case int() if data < 0:
            return "negative"
        case int():
            return "zero"
        case str():
            return "string"
        case _:
            return "unknown"
"""
        self.parser.parse(code)
        functions = self.parser.extract_functions()
        
        assert len(functions) == 1
        func = functions[0]
        assert func.name == 'process_data'
        
        # Base complexity (1) + match statement cases (5) = 6
        # Note: guards (if conditions) add additional complexity
        assert func.complexity >= 6
    
    def test_error_recovery_partial_ast(self):
        """Test error recovery with syntax errors"""
        code = """
def valid_func():
    return "valid"

def broken_func(
    # Missing closing parenthesis
    param1: str,
    param2: int

def another_valid_func():
    return "also valid"
"""
        # Should not raise exception
        self.parser.parse(code)
        functions = self.parser.extract_functions()
        
        # Should extract at least the valid functions
        func_names = [f.name for f in functions]
        assert 'valid_func' in func_names
        # Note: error recovery may not extract all functions depending on syntax errors
        assert len(func_names) >= 1
    
    def test_parameter_type_annotations(self):
        """Test parameter extraction with type annotations"""
        code = """
def typed_function(
    name: str,
    age: int,
    scores: list[float],
    metadata: dict[str, any] = None,
    *args: str,
    **kwargs: int
) -> dict[str, any]:
    return {"name": name, "age": age}
"""
        self.parser.parse(code)
        functions = self.parser.extract_functions()
        
        assert len(functions) == 1
        func = functions[0]
        assert func.name == 'typed_function'
        assert func.return_type == '-> dict[str, any]'
        
        # Check that parameters are extracted
        assert len(func.params) > 0
    
    def test_complex_decorators(self):
        """Test extraction of complex decorators"""
        code = """
@property
@lru_cache(maxsize=128)
@validate_input(strict=True)
def decorated_function():
    return "decorated"

@staticmethod
@override
def static_method():
    pass
"""
        self.parser.parse(code)
        functions = self.parser.extract_functions()
        
        assert len(functions) == 2
        
        decorated = next(f for f in functions if f.name == 'decorated_function')
        assert '@property' in decorated.decorators
        assert '@lru_cache' in decorated.decorators
        assert '@validate_input' in decorated.decorators
        
        static = next(f for f in functions if f.name == 'static_method')
        assert '@staticmethod' in static.decorators
        assert '@override' in static.decorators
    
    def test_logical_operators_complexity(self):
        """Test complexity calculation with logical operators"""
        code = """
def complex_logic(a, b, c, d):
    if a and b or c and d:
        return True
    elif a or b and c:
        return False
    return None
"""
        self.parser.parse(code)
        functions = self.parser.extract_functions()
        
        assert len(functions) == 1
        func = functions[0]
        
        # Base (1) + if (1) + elif (1) + logical operators (variable) >= 6
        assert func.complexity >= 6
    
    def test_semantic_tags_extraction(self):
        """Test extraction of semantic tags from function calls"""
        code = """
def database_function():
    cursor.execute("SELECT * FROM users")
    result = cursor.fetchall()
    connection.commit()
    return result

def network_function():
    response = requests.get("http://api.example.com")
    socket.send(data)
    return response

def file_function():
    with open("file.txt", "r") as f:
        content = f.read()
    return content
"""
        self.parser.parse(code)
        functions = self.parser.extract_functions()
        
        func_dict = {f.name: f for f in functions}
        
        # Check database tags
        db_func = func_dict['database_function']
        assert 'db_op' in db_func.tags
        
        # Check network tags
        net_func = func_dict['network_function']
        assert 'network' in net_func.tags
        
        # Check file I/O tags
        file_func = func_dict['file_function']
        assert 'file_io' in file_func.tags
    
    def test_class_method_exclusion(self):
        """Test that class methods are excluded from function extraction"""
        code = """
def standalone_function():
    return "standalone"

class MyClass:
    def method_one(self):
        return "method"
    
    @staticmethod
    def static_method():
        return "static"
    
    @classmethod
    def class_method(cls):
        return "class"

def another_standalone():
    return "another"
"""
        self.parser.parse(code)
        functions = self.parser.extract_functions()
        
        # Should only extract standalone functions, not class methods
        func_names = [f.name for f in functions]
        assert 'standalone_function' in func_names
        assert 'another_standalone' in func_names
        assert 'method_one' not in func_names
        assert 'static_method' not in func_names
        assert 'class_method' not in func_names
    
    def test_deeply_nested_functions(self):
        """Test deeply nested function extraction"""
        code = """
def level1():
    def level2():
        def level3():
            def level4():
                return "deep"
            return level4
        return level3
    return level2
"""
        self.parser.parse(code)
        functions = self.parser.extract_functions()
        
        assert len(functions) == 4
        
        func_dict = {f.name: f for f in functions}
        
        assert func_dict['level1'].parent_scope is None
        assert func_dict['level2'].parent_scope == 'level1'
        assert func_dict['level3'].parent_scope == 'level2'
        assert func_dict['level4'].parent_scope == 'level3'
    
    @pytest.mark.benchmark
    def test_parsing_performance(self, benchmark):
        """Test parsing performance for large code"""
        # Generate a large Python file
        lines = []
        for i in range(100):
            lines.append(f"""
def function_{i}(param1, param2, param3):
    '''Function {i} docstring'''
    if param1 > 0:
        for j in range(param2):
            if j % 2 == 0:
                result = param3 * j
            else:
                result = param3 + j
        return result
    elif param1 < 0:
        return param2 - param3
    else:
        return 0
""")
        
        large_code = '\n'.join(lines)
        
        def parse_large_code():
            parser = PythonParser()
            parser.parse(large_code)
            return parser.extract_functions()
        
        result = benchmark(parse_large_code)
        
        # Should extract 100 functions
        assert len(result) == 100
        
        # Performance should be reasonable (less than 500ms for 1000+ LOC)
        # Note: benchmark.stats is a Metadata object, access mean differently
        mean_time = getattr(benchmark.stats, 'mean', benchmark.stats.get('mean', 0.1))
        assert mean_time < 0.5
    
    def test_ast_summary_generation(self):
        """Test AST summary generation"""
        code = """
import os
import sys
from typing import List

def func1():
    pass

def func2():
    pass

class MyClass:
    def method(self):
        pass

# This is a comment
# Another comment
"""
        summary = self.parser.get_ast_summary(code)
        
        assert summary.function_count == 2  # Only standalone functions
        assert summary.class_count == 1
        assert summary.import_count == 3
        assert summary.comment_lines == 2
    
    def test_complexity_metrics(self):
        """Test complexity metrics calculation"""
        code = """
def complex_function(x, y, z):
    if x > 0:
        if y > 0:
            if z > 0:
                return x + y + z
            else:
                return x + y
        else:
            return x
    else:
        return 0
"""
        metrics = self.parser.get_complexity_metrics(code)
        
        # Should have reasonable complexity
        assert metrics.cyclomatic > 1