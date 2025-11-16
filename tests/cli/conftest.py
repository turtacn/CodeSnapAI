import pytest
from rich.console import Console
from io import StringIO

@pytest.fixture
def mock_rich_console():
    """Fixture to capture rich console output."""
    console = Console(file=StringIO(), force_terminal=True)
    yield console
