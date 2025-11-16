from click.testing import CliRunner
from codesage.cli.main import main
import os
from unittest.mock import patch

@patch('questionary.confirm')
@patch('questionary.text')
@patch('questionary.checkbox')
def test_interactive_wizard(mock_checkbox, mock_text, mock_confirm, tmp_path):
    """Test the interactive wizard."""
    runner = CliRunner()

    # Mock the return values of the questionary prompts
    mock_checkbox.return_value.ask.side_effect = [
        ['python', 'go'],  # languages
        ['json', 'markdown']  # snapshot formats
    ]
    mock_text.return_value.ask.side_effect = [
        ".*,node_modules",  # exclude
        "15",  # complexity threshold
        "15",  # max versions
        "45"   # retention days
    ]
    mock_confirm.return_value.ask.return_value = True

    with runner.isolated_filesystem(temp_dir=tmp_path):
        result = runner.invoke(main, ['config', 'init', '--interactive'])

        assert result.exit_code == 0
        assert os.path.exists('.codesage.yaml')
        with open('.codesage.yaml', 'r') as f:
            content = f.read()
            assert "python" in content
            assert "go" in content
            assert "node_modules" in content
            assert "15" in content
            assert "45" in content
