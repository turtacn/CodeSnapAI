from pydantic import BaseModel
from typing import List, Optional

class FunctionNode(BaseModel):
    name: str
    params: List[str]
    return_type: Optional[str]
    start_line: int
    end_line: int
    complexity: int
    is_async: bool = False
    decorators: List[str] = []

class ClassNode(BaseModel):
    name: str
    methods: List[FunctionNode]
    base_classes: List[str]

class ImportNode(BaseModel):
    module: str
    alias: Optional[str]
    is_relative: bool = False

class FileAST(BaseModel):
    language: str
    functions: List[FunctionNode]
    classes: List[ClassNode]
    imports: List[ImportNode]
