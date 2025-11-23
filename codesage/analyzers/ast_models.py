from typing import List, Optional, Any
from pydantic import BaseModel

class ASTNode(BaseModel):
    node_type: str
    start_line: int = 0
    end_line: int = 0
    children: List['ASTNode'] = []
    # A generic property to hold things like operator/operand values
    value: Any = None

class VariableNode(ASTNode):
    name: str
    value: Optional[str] = None
    kind: str = "global"  # global, local, field (for structs)
    type_name: Optional[str] = None # For typed variables (Go)
    is_exported: bool = False

class FunctionNode(ASTNode):
    name: str
    params: List[str] = []
    return_type: Optional[str] = None
    receiver: Optional[str] = None # For Go methods
    is_async: bool = False
    decorators: List[str] = []
    complexity: int = 1
    # Assuming complexity from P2 is stored here
    cyclomatic_complexity: int = 1
    cognitive_complexity: int = 0

class ClassNode(ASTNode):
    name: str
    methods: List[FunctionNode] = []
    fields: List[VariableNode] = [] # For structs
    base_classes: List[str] = []

class ImportNode(ASTNode):
    path: str
    alias: Optional[str] = None

class FileAST(BaseModel):
    path: str
    functions: List[FunctionNode] = []
    classes: List[ClassNode] = [] # Classes, Structs, Interfaces
    variables: List[VariableNode] = []
    imports: List[ImportNode] = []
    # The root of the raw AST tree
    tree: Optional[ASTNode] = None
