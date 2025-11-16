import click
import os
import sys

def validate_path(ctx, param, value):
    """Click callback to validate a path."""
    if not os.path.exists(value):
        raise click.BadParameter(f"Path '{value}' does not exist.")
    return value

def validate_language(ctx, param, value):
    """Click callback to validate a language."""
    # In a real application, this would come from a config file or a list of supported parsers.
    supported_languages = ['python', 'go']
    if value not in supported_languages:
        raise click.BadParameter(f"Unsupported language '{value}'. Supported languages are: {supported_languages}")
    return value

def handle_errors(func):
    """Decorator to catch common exceptions and provide friendly error messages."""
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except FileNotFoundError as e:
            click.echo(f"Error: File not found at path: {e.filename}", err=True)
            sys.exit(1)
        except click.ClickException:
            raise
        except Exception as e:
            click.echo(f"An unexpected error occurred: {e}", err=True)
            sys.exit(1)
    return wrapper
