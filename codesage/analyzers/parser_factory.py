from codesage.analyzers.base import BaseParser
from codesage.analyzers.go_parser import GoParser
from codesage.analyzers.python_parser import PythonParser
from codesage.analyzers.java_parser import JavaParser

PARSERS = {
    "go": GoParser,
    "python": PythonParser,
    "java": JavaParser,
}

def create_parser(language: str) -> BaseParser:
    parser = PARSERS.get(language)
    if not parser:
        raise ValueError(f"Unsupported language: {language}. Supported languages are: {list(PARSERS.keys())}")
    return parser()

def detect_language(file_path: str) -> str:
    """Detect programming language from file extension."""
    from pathlib import Path
    
    ext = Path(file_path).suffix.lower()
    
    language_map = {
        '.py': 'python',
        '.go': 'go', 
        '.java': 'java',
        '.js': 'javascript',
        '.ts': 'typescript',
        '.jsx': 'javascript',
        '.tsx': 'typescript',
        '.c': 'c',
        '.cpp': 'cpp',
        '.cc': 'cpp',
        '.cxx': 'cpp',
        '.h': 'c',
        '.hpp': 'cpp',
        '.hh': 'cpp',
        '.hxx': 'cpp',
        '.sh': 'shell',
        '.bash': 'shell',
        '.zsh': 'shell'
    }
    
    return language_map.get(ext, 'unknown')
