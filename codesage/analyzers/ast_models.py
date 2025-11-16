from typing import List, Optional, Any
from pydantic import BaseModel

class ASTNode(BaseModel):
    node_type: str
    start_line: int = 0
    end_line: int = 0
    children: List['ASTNode'] = []
    # A generic property to hold things like operator/operand values
    value: Any = None

class FunctionNode(ASTNode):
    name: str
    params: List[str] = []
    return_type: Optional[str] = None
    is_async: bool = False
    decorators: List[str] = []
    complexity: int = 1
    # Assuming complexity from P2 is stored here
    cyclomatic_complexity: int = 1
    cognitive_complexity: int = 0

class ClassNode(ASTNode):
    name: str
    methods: List[FunctionNode] = []

class ImportNode(ASTNode):
    path: str

class FileAST(BaseModel):
    path: str
    functions: List[FunctionNode] = []
    classes: List[ClassNode] = []
    imports: List[ImportNode] = []
    # The root of the raw AST tree
    tree: Optional[ASTNode] = None
