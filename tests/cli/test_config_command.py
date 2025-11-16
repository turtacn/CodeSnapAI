from click.testing import CliRunner
from codesage.cli.main import main
import os

def test_config_init(tmp_path):
    """Test the config init command."""
    runner = CliRunner()
    with runner.isolated_filesystem(temp_dir=tmp_path):
        result = runner.invoke(main, ['config', 'init'])

        assert result.exit_code == 0
        assert os.path.exists('.codesage.yaml')
        assert "Configuration file created" in result.output

def test_config_show(tmp_path):
    """Test the config show command."""
    runner = CliRunner()
    with runner.isolated_filesystem(temp_dir=tmp_path):
        with open('.codesage.yaml', 'w') as f:
            f.write("cli:\n  log_level: debug")

        result = runner.invoke(main, ['config', 'show'])

        assert result.exit_code == 0
        assert "log_level: debug" in result.output
