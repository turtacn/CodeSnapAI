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
