from rich.progress import Progress, SpinnerColumn, BarColumn, TextColumn
from rich.console import Console

console = Console()

def create_progress_bar(total: int, description: str):
    """Creates a rich progress bar."""
    return Progress(
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        TextColumn("({task.completed} of {task.total})")
    )

def create_spinner(description: str):
    """Creates a rich spinner."""
    return Progress(
        TextColumn("[progress.description]{task.description}"),
        SpinnerColumn(),
    )

def display_status(message: str, style: str = "info"):
    """Displays a status message."""
    if style == "info":
        console.print(f"[blue]i[/blue] {message}")
    elif style == "success":
        console.print(f"[green]✓[/green] {message}")
    elif style == "warning":
        console.print(f"[yellow]![/yellow] {message}")
    elif style == "error":
        console.print(f"[red]✗[/red] {message}")
    else:
        console.print(message)
