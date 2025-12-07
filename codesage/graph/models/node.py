"""
Graph node models representing different code entities.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field
import hashlib


class Node(BaseModel, ABC):
    """Base class for all graph nodes."""
    
    id: str = Field(..., description="Unique identifier for the node")
    type: str = Field(..., description="Node type (function, class, file, etc.)")
    properties: Dict[str, Any] = Field(default_factory=dict, description="Node properties")
    
    class Config:
        frozen = True
    
    def __hash__(self) -> int:
        return hash(self.id)
    
    def __eq__(self, other) -> bool:
        if not isinstance(other, Node):
            return False
        return self.id == other.id
    
    @abstractmethod
    def get_qualified_name(self) -> str:
        """Get the fully qualified name of this node."""
        pass
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert node to dictionary for serialization."""
        return {
            'id': self.id,
            'type': self.type,
            'properties': self.properties
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Node':
        """Create node from dictionary."""
        node_type = data['type']
        properties = data.get('properties', {})
        
        node_classes = {
            'file': FileNode,
            'module': ModuleNode,
            'function': FunctionNode,
            'class': ClassNode,
            'variable': VariableNode
        }
        
        node_class = node_classes.get(node_type)
        if not node_class:
            raise ValueError(f"Unknown node type: {node_type}")
        
        # Create node with proper constructor arguments
        if node_class == FileNode:
            return node_class(
                id=data['id'],
                path=properties.get('path', ''),
                language=properties.get('language', ''),
                loc=properties.get('loc', 0),
                **{k: v for k, v in properties.items() 
                   if k not in ('path', 'language', 'loc')}
            )
        elif node_class == ModuleNode:
            return node_class(
                id=data['id'],
                name=properties.get('name', ''),
                qualified_name=properties.get('qualified_name', ''),
                **{k: v for k, v in properties.items() 
                   if k not in ('name', 'qualified_name')}
            )
        elif node_class == FunctionNode:
            return node_class(
                id=data['id'],
                name=properties.get('name', ''),
                qualified_name=properties.get('qualified_name', ''),
                line_start=properties.get('line_start', 0),
                line_end=properties.get('line_end', 0),
                complexity=properties.get('complexity', 0),
                params=properties.get('params', []),
                return_type=properties.get('return_type'),
                **{k: v for k, v in properties.items() 
                   if k not in ('name', 'qualified_name', 'line_start', 'line_end', 'complexity', 'params', 'return_type')}
            )
        elif node_class == ClassNode:
            return node_class(
                id=data['id'],
                name=properties.get('name', ''),
                qualified_name=properties.get('qualified_name', ''),
                line_start=properties.get('line_start', 0),
                line_end=properties.get('line_end', 0),
                base_classes=properties.get('base_classes', []),
                methods=properties.get('methods', []),
                **{k: v for k, v in properties.items() 
                   if k not in ('name', 'qualified_name', 'line_start', 'line_end', 'base_classes', 'methods')}
            )
        elif node_class == VariableNode:
            return node_class(
                id=data['id'],
                name=properties.get('name', ''),
                qualified_name=properties.get('qualified_name', ''),
                **{k: v for k, v in properties.items() 
                   if k not in ('name', 'qualified_name')}
            )
        else:
            # Fallback to generic node
            return Node(
                id=data['id'],
                type=data['type'],
                properties=properties
            )


class FileNode(Node):
    """Represents a source code file."""
    
    def __init__(self, id: str, path: str, language: str, loc: int, **kwargs):
        properties = {
            'path': path,
            'language': language,
            'loc': loc,
            **kwargs
        }
        super().__init__(id=id, type='file', properties=properties)
    
    @property
    def path(self) -> str:
        return self.properties['path']
    
    @property
    def language(self) -> str:
        return self.properties['language']
    
    @property
    def loc(self) -> int:
        return self.properties['loc']
    
    def get_qualified_name(self) -> str:
        return self.path


class ModuleNode(Node):
    """Represents a module or package."""
    
    def __init__(self, id: str, name: str, qualified_name: str, **kwargs):
        properties = {
            'name': name,
            'qualified_name': qualified_name,
            **kwargs
        }
        super().__init__(id=id, type='module', properties=properties)
    
    @property
    def name(self) -> str:
        return self.properties['name']
    
    @property
    def qualified_name(self) -> str:
        return self.properties['qualified_name']
    
    def get_qualified_name(self) -> str:
        return self.qualified_name


class FunctionNode(Node):
    """Represents a function or method."""
    
    def __init__(self, id: str, name: str, qualified_name: str, 
                 line_start: int, line_end: int, **kwargs):
        properties = {
            'name': name,
            'qualified_name': qualified_name,
            'line_start': line_start,
            'line_end': line_end,
            **kwargs
        }
        super().__init__(id=id, type='function', properties=properties)
    
    @property
    def name(self) -> str:
        return self.properties['name']
    
    @property
    def qualified_name(self) -> str:
        return self.properties['qualified_name']
    
    @property
    def line_start(self) -> int:
        return self.properties['line_start']
    
    @property
    def line_end(self) -> int:
        return self.properties['line_end']
    
    @property
    def complexity(self) -> Optional[int]:
        return self.properties.get('complexity')
    
    @property
    def params(self) -> List[str]:
        return self.properties.get('params', [])
    
    @property
    def return_type(self) -> Optional[str]:
        return self.properties.get('return_type')
    
    def get_qualified_name(self) -> str:
        return self.qualified_name


class ClassNode(Node):
    """Represents a class definition."""
    
    def __init__(self, id: str, name: str, qualified_name: str,
                 line_start: int, line_end: int, **kwargs):
        properties = {
            'name': name,
            'qualified_name': qualified_name,
            'line_start': line_start,
            'line_end': line_end,
            **kwargs
        }
        super().__init__(id=id, type='class', properties=properties)
    
    @property
    def name(self) -> str:
        return self.properties['name']
    
    @property
    def qualified_name(self) -> str:
        return self.properties['qualified_name']
    
    @property
    def line_start(self) -> int:
        return self.properties['line_start']
    
    @property
    def line_end(self) -> int:
        return self.properties['line_end']
    
    @property
    def base_classes(self) -> List[str]:
        return self.properties.get('base_classes', [])
    
    @property
    def methods(self) -> List[str]:
        return self.properties.get('methods', [])
    
    def get_qualified_name(self) -> str:
        return self.qualified_name


class VariableNode(Node):
    """Represents a variable or constant."""
    
    def __init__(self, id: str, name: str, qualified_name: str, **kwargs):
        properties = {
            'name': name,
            'qualified_name': qualified_name,
            **kwargs
        }
        super().__init__(id=id, type='variable', properties=properties)
    
    @property
    def name(self) -> str:
        return self.properties['name']
    
    @property
    def qualified_name(self) -> str:
        return self.properties['qualified_name']
    
    @property
    def type_hint(self) -> Optional[str]:
        return self.properties.get('type_hint')
    
    @property
    def value(self) -> Optional[str]:
        return self.properties.get('value')
    
    def get_qualified_name(self) -> str:
        return self.qualified_name


def create_node_id(node_type: str, qualified_name: str, file_path: Optional[str] = None) -> str:
    """Create a unique node ID based on type, qualified name, and optional file path."""
    if file_path:
        base = f"{file_path}:{qualified_name}"
    else:
        base = qualified_name
    
    # Create a hash for very long names to keep IDs manageable
    if len(base) > 200:
        hash_suffix = hashlib.md5(base.encode()).hexdigest()[:8]
        base = f"{base[:180]}...{hash_suffix}"
    
    return f"{node_type}:{base}"