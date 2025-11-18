import pytest
from codesage.risk.python_complexity import analyze_file_complexity

def test_simple_function_complexity():
    code = """
def my_func(a, b):
    if a > b:
        return a
    return b
"""
    result = analyze_file_complexity(code)
    assert result.max_cyclomatic_complexity == 2
    assert result.avg_cyclomatic_complexity == 2.0
    assert result.high_complexity_functions == 0

def test_branchy_function_high_complexity():
    code = """
def my_func(a, b, c):
    if a > b:
        if b > c:
            for i in range(10):
                while True:
                    try:
                        if a and b or c:
                            pass
                    except:
                        pass
    return b
"""
    result = analyze_file_complexity(code, high_complexity_threshold=5)
    assert result.max_cyclomatic_complexity > 5
    assert result.high_complexity_functions == 1

def test_file_level_metrics_aggregate():
    code = """
def func1(a, b):
    if a > b:
        return a
    return b

def func2(a, b):
    if a > b:
        return a
    else:
        return b
"""
    result = analyze_file_complexity(code)
    assert result.loc == 11
    assert result.num_functions == 2
    assert result.max_cyclomatic_complexity == 2
    assert result.avg_cyclomatic_complexity == 2.0
