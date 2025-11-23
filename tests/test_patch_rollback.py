import shutil
from pathlib import Path
from codesage.governance.patch_manager import PatchManager

def test_patch_manager_backup_restore(tmp_path):
    pm = PatchManager()
    file_path = tmp_path / "target.txt"
    file_path.write_text("Original Content")

    # Apply Patch with backup
    pm.apply_patch(file_path, "New Content", create_backup=True)

    assert file_path.read_text() == "New Content"
    assert (tmp_path / "target.txt.bak").exists()
    assert (tmp_path / "target.txt.bak").read_text() == "Original Content"

    # Revert
    pm.revert(file_path)

    assert file_path.read_text() == "Original Content"
    # Revert moves the backup back, so backup file should be gone (shutil.move)
    assert not (tmp_path / "target.txt.bak").exists()

def test_patch_manager_cleanup(tmp_path):
    pm = PatchManager()
    file_path = tmp_path / "target.txt"
    file_path.write_text("Original Content")

    # Create manual backup
    backup_path = tmp_path / "target.txt.bak"
    shutil.copy2(file_path, backup_path)

    pm.cleanup_backup(file_path)

    assert not backup_path.exists()
