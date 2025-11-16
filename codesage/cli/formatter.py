import json
from rich.table import Table
from rich.syntax import Syntax
from rich.console import Console

console = Console()

def format_table(data, columns, title=None):
    """Formats data into a rich table."""
    table = Table(title=title)
    for col in columns:
        table.add_column(col)
    for row in data:
        table.add_row(*[str(item) for item in row])
    return table

def format_json(data, pretty=True):
    """Formats data as a JSON string."""
    if pretty:
        return json.dumps(data, indent=2)
    else:
        return json.dumps(data, separators=(',', ':'))

def colorize_complexity(value, thresholds):
    """Colorizes a complexity value based on thresholds."""
    if value < thresholds.get('low', 5):
        return f"[green]{value}[/green]"
    elif value < thresholds.get('medium', 10):
        return f"[yellow]{value}[/yellow]"
    else:
        return f"[red]{value}[/red]"

def highlight_code(code, language):
    """Highlights a code snippet using rich."""
    return Syntax(code, language, theme="monokai", line_numbers=True)
