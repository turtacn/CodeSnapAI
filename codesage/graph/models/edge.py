"""
Graph edge models representing relationships between code entities.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field


class Edge(BaseModel, ABC):
    """Base class for all graph edges."""
    
    source: str = Field(..., description="Source node ID")
    target: str = Field(..., description="Target node ID")
    type: str = Field(..., description="Edge type (calls, inherits, etc.)")
    properties: Dict[str, Any] = Field(default_factory=dict, description="Edge properties")
    
    class Config:
        frozen = True
    
    def __hash__(self) -> int:
        return hash((self.source, self.target, self.type))
    
    def __eq__(self, other) -> bool:
        if not isinstance(other, Edge):
            return False
        return (self.source == other.source and 
                self.target == other.target and 
                self.type == other.type)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert edge to dictionary for serialization."""
        return {
            'source': self.source,
            'target': self.target,
            'type': self.type,
            'properties': self.properties
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Edge':
        """Create edge from dictionary."""
        edge_type = data['type']
        properties = data.get('properties', {})
        
        edge_classes = {
            'contains': ContainsEdge,
            'calls': CallEdge,
            'inherits': InheritanceEdge,
            'imports': ImportEdge,
            'references': ReferencesEdge,
            'defines': DefinesEdge
        }
        
        edge_class = edge_classes.get(edge_type)
        if not edge_class:
            raise ValueError(f"Unknown edge type: {edge_type}")
        
        # Create edge with proper constructor arguments
        if edge_class == CallEdge:
            return edge_class(
                source=data['source'],
                target=data['target'],
                call_site=properties.get('call_site'),
                **{k: v for k, v in properties.items() if k != 'call_site'}
            )
        elif edge_class == InheritanceEdge:
            return edge_class(
                source=data['source'],
                target=data['target'],
                inheritance_type=properties.get('inheritance_type', 'extends'),
                **{k: v for k, v in properties.items() if k != 'inheritance_type'}
            )
        elif edge_class == ImportEdge:
            return edge_class(
                source=data['source'],
                target=data['target'],
                import_type=properties.get('import_type', 'import'),
                alias=properties.get('alias'),
                **{k: v for k, v in properties.items() if k not in ('import_type', 'alias')}
            )
        else:
            # Generic edge types
            return edge_class(
                source=data['source'],
                target=data['target'],
                **properties
            )


class ContainsEdge(Edge):
    """Represents a containment relationship (file contains function)."""
    
    def __init__(self, source: str, target: str, **kwargs):
        properties = kwargs
        super().__init__(source=source, target=target, type='contains', properties=properties)
    
    @property
    def line_number(self) -> Optional[int]:
        return self.properties.get('line_number')


class CallEdge(Edge):
    """Represents a function call relationship."""
    
    def __init__(self, source: str, target: str, call_site: Optional[int] = None, **kwargs):
        properties = kwargs
        if call_site is not None:
            properties['call_site'] = call_site
        super().__init__(source=source, target=target, type='calls', properties=properties)
    
    @property
    def call_site(self) -> Optional[int]:
        return self.properties.get('call_site')
    
    @property
    def call_type(self) -> str:
        return self.properties.get('call_type', 'direct')
    
    @property
    def arguments(self) -> Optional[str]:
        return self.properties.get('arguments')


class InheritanceEdge(Edge):
    """Represents a class inheritance relationship."""
    
    def __init__(self, source: str, target: str, **kwargs):
        properties = kwargs
        super().__init__(source=source, target=target, type='inherits', properties=properties)
    
    @property
    def inheritance_type(self) -> str:
        return self.properties.get('inheritance_type', 'single')


class ImportEdge(Edge):
    """Represents an import relationship."""
    
    def __init__(self, source: str, target: str, import_type: str = 'import', **kwargs):
        properties = {'import_type': import_type, **kwargs}
        super().__init__(source=source, target=target, type='imports', properties=properties)
    
    @property
    def import_type(self) -> str:
        return self.properties['import_type']
    
    @property
    def alias(self) -> Optional[str]:
        return self.properties.get('alias')
    
    @property
    def line_number(self) -> Optional[int]:
        return self.properties.get('line_number')


class ReferencesEdge(Edge):
    """Represents a variable reference relationship."""
    
    def __init__(self, source: str, target: str, reference_type: str = 'read', **kwargs):
        properties = {'reference_type': reference_type, **kwargs}
        super().__init__(source=source, target=target, type='references', properties=properties)
    
    @property
    def reference_type(self) -> str:
        return self.properties['reference_type']
    
    @property
    def line_number(self) -> Optional[int]:
        return self.properties.get('line_number')


class DefinesEdge(Edge):
    """Represents a definition relationship."""
    
    def __init__(self, source: str, target: str, definition_type: str = 'local', **kwargs):
        properties = {'definition_type': definition_type, **kwargs}
        super().__init__(source=source, target=target, type='defines', properties=properties)
    
    @property
    def definition_type(self) -> str:
        return self.properties['definition_type']
    
    @property
    def line_number(self) -> Optional[int]:
        return self.properties.get('line_number')