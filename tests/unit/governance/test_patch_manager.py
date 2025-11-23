import pytest
from pathlib import Path
from codesage.governance.patch_manager import PatchManager

@pytest.fixture
def patch_manager():
    return PatchManager()

@pytest.fixture
def temp_file(tmp_path):
    p = tmp_path / "test_file.py"
    p.write_text("def hello():\n    print('hello')\n", encoding="utf-8")
    return p

class TestPatchManager:
    def test_extract_code_block_python(self, patch_manager):
        llm_response = "Here is the fix:\n```python\ndef hello():\n    print('world')\n```\nHope this helps."
        code = patch_manager.extract_code_block(llm_response, language="python")
        assert code.strip() == "def hello():\n    print('world')"

    def test_extract_code_block_generic(self, patch_manager):
        llm_response = "```\ndef hello():\n    print('world')\n```"
        code = patch_manager.extract_code_block(llm_response)
        assert code.strip() == "def hello():\n    print('world')"

    def test_extract_code_block_no_match(self, patch_manager):
        llm_response = "Just some text."
        code = patch_manager.extract_code_block(llm_response)
        assert code is None

    def test_apply_patch_clean(self, patch_manager, temp_file):
        new_content = "def hello():\n    print('world')\n"
        result = patch_manager.apply_patch(temp_file, new_content)

        assert result is True
        assert temp_file.read_text(encoding="utf-8") == new_content

        # Check backup
        backup = temp_file.with_suffix(".py.bak")
        assert backup.exists()
        assert "print('hello')" in backup.read_text(encoding="utf-8")

    def test_restore_backup(self, patch_manager, temp_file):
        # Create a backup manually
        backup = temp_file.with_suffix(".py.bak")
        backup.write_text("def original(): pass", encoding="utf-8")

        # Modify original
        temp_file.write_text("def modified(): pass", encoding="utf-8")

        result = patch_manager.restore_backup(temp_file)
        assert result is True
        assert temp_file.read_text(encoding="utf-8") == "def original(): pass"
        assert not backup.exists() # Move consumes the file? shutil.move does.

    def test_create_diff(self, patch_manager):
        original = "line1\nline2\n"
        new = "line1\nline2 modified\n"
        diff = patch_manager.create_diff(original, new, "test.txt")

        assert "--- a/test.txt" in diff
        assert "+++ b/test.txt" in diff
        assert "-line2" in diff
        assert "+line2 modified" in diff
