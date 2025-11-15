import pytest
from codesage.analyzers.python_parser import PythonParser

@pytest.fixture
def python_parser():
    return PythonParser()

@pytest.fixture
def sample_python_code():
    with open('tests/fixtures/sample.py', 'r') as f:
        return f.read()

def test_extract_class_methods_python(python_parser, sample_python_code):
    python_parser.parse(sample_python_code)
    classes = python_parser.extract_classes()
    assert len(classes) == 1
    assert classes[0].name == 'MyClass'
    assert len(classes[0].methods) == 3

def test_detect_async_function_python(python_parser):
    code = "async def async_func(): await asyncio.sleep(1)"
    python_parser.parse(code)
    functions = python_parser.extract_functions()
    assert len(functions) == 1
    assert functions[0].is_async is True

def test_extract_decorators_python(python_parser):
    code = """
@decorator
def decorated_func():
    pass
    """
    python_parser.parse(code)
    functions = python_parser.extract_functions()
    assert len(functions) == 1
    assert functions[0].decorators == ['@decorator']

def test_calculate_complexity_python(python_parser):
    code = """
def complex_func(a, b):
    if a:
        if b:
            return 1
    for i in range(10):
        try:
            pass
        except:
            pass
    return 0
    """
    python_parser.parse(code)
    functions = python_parser.extract_functions()
    assert functions[0].complexity >= 8

def test_parse_type_hints_python(python_parser):
    code = "def foo(x: int) -> str: pass"
    python_parser.parse(code)
    functions = python_parser.extract_functions()
    assert len(functions) == 1
    assert functions[0].return_type == '-> str'
