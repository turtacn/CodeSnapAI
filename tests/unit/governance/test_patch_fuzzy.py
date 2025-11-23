import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch
from codesage.governance.patch_manager import PatchManager

class TestPatchFuzzy:
    @pytest.fixture
    def patch_manager(self):
        return PatchManager()

    def test_fuzzy_replace_function(self, patch_manager, tmp_path):
        # Create a dummy file with a function
        file_path = tmp_path / "calc.py"
        original_code = """
def add(a, b):
    return a + b

def subtract(a, b):
    return a - b
"""
        file_path.write_text(original_code, encoding="utf-8")

        # LLM generated replacement for 'add' with a comment
        new_block = """def add(a, b):
    # Added comment
    return a + b
"""
        # Test symbol replacement
        success = patch_manager.apply_fuzzy_patch(file_path, new_block, target_symbol="add")
        assert success

        content = file_path.read_text(encoding="utf-8")
        assert "# Added comment" in content
        assert "def subtract(a, b):" in content # Ensure other code is preserved

    def test_context_patch(self, patch_manager, tmp_path):
        # Test context patch when symbol is not provided
        file_path = tmp_path / "utils.py"
        original_code = """
def greet(name):
    print(f"Hello {name}")

def farewell(name):
    print(f"Goodbye {name}")
"""
        file_path.write_text(original_code, encoding="utf-8")

        # New block slightly different
        new_block = """def greet(name):
    print(f"Hi {name}")
"""
        # Apply fuzzy patch without symbol
        success = patch_manager.apply_fuzzy_patch(file_path, new_block)
        assert success

        content = file_path.read_text(encoding="utf-8")
        assert 'print(f"Hi {name}")' in content
        assert 'print(f"Goodbye {name}")' in content

    def test_extract_code_block(self, patch_manager):
        response = """
Here is the code:
```python
def foo():
    pass
```
"""
        extracted = patch_manager.extract_code_block(response, language="python")
        assert extracted.strip() == "def foo():\n    pass"

    def test_syntax_check_python(self, patch_manager):
        valid_code = "def foo(): pass"
        invalid_code = "def foo() pass" # Missing colon

        assert patch_manager._verify_syntax(valid_code, "python") is True
        assert patch_manager._verify_syntax(invalid_code, "python") is False
