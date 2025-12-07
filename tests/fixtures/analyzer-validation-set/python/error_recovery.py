"""
Test case for error recovery - contains syntax errors
"""

def valid_function():
    """This function should be parsed correctly"""
    return "valid"

def function_with_syntax_error(
    # Missing closing parenthesis - syntax error
    param1: str,
    param2: int
    # Missing closing parenthesis here

def another_valid_function():
    """This should also be parsed despite previous error"""
    if True:
        return "also valid"

class ValidClass:
    """This class should be parsed correctly"""
    
    def method_one(self):
        return "method one"
    
    def method_with_error(self
        # Missing closing parenthesis
        return "error method"
    
    def method_two(self):
        """This method should still be parsed"""
        return "method two"

# Incomplete function definition
def incomplete_function(
    param1: str
    # Missing closing parenthesis and body

# This should still be parsed
def final_valid_function():
    """Final function that should be parsed"""
    return "final"