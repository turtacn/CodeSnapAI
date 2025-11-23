from typing import List, Optional, Any, Set
from pydantic import BaseModel, Field

class ASTNode(BaseModel):
    node_type: str
    start_line: int = 0
    end_line: int = 0
    children: List['ASTNode'] = Field(default_factory=list)
    # A generic property to hold things like operator/operand values
    value: Any = None
    tags: Set[str] = Field(default_factory=set)

class VariableNode(ASTNode):
    name: str
    value: Optional[str] = None
    kind: str = "global"  # global, local, field (for structs)
    type_name: Optional[str] = None # For typed variables (Go)
    is_exported: bool = False

class FunctionNode(ASTNode):
    name: str
    params: List[str] = Field(default_factory=list)
    return_type: Optional[str] = None
    receiver: Optional[str] = None # For Go methods
    is_async: bool = False
    decorators: List[str] = Field(default_factory=list)
    complexity: int = 1
    # Assuming complexity from P2 is stored here
    cyclomatic_complexity: int = 1
    cognitive_complexity: int = 0
    is_exported: bool = False

class ClassNode(ASTNode):
    name: str
    methods: List[FunctionNode] = Field(default_factory=list)
    fields: List[VariableNode] = Field(default_factory=list) # For structs
    base_classes: List[str] = Field(default_factory=list)
    is_exported: bool = False

class ImportNode(ASTNode):
    path: str
    alias: Optional[str] = None
    is_relative: bool = False

class FileAST(BaseModel):
    path: str
    functions: List[FunctionNode] = Field(default_factory=list)
    classes: List[ClassNode] = Field(default_factory=list) # Classes, Structs, Interfaces
    variables: List[VariableNode] = Field(default_factory=list)
    imports: List[ImportNode] = Field(default_factory=list)
    # The root of the raw AST tree
    tree: Optional[ASTNode] = None
