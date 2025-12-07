"""
Graph builder for converting parser output to semantic graphs.
"""

import os
import logging
from typing import Dict, Any, Optional, List, Set
from collections import defaultdict
import yaml

from .models.graph import Graph
from .models.node import (
    Node, FileNode, ModuleNode, FunctionNode, ClassNode, VariableNode, create_node_id
)
from .models.edge import (
    Edge, ContainsEdge, CallEdge, InheritanceEdge, ImportEdge, ReferencesEdge, DefinesEdge
)

logger = logging.getLogger(__name__)


class GraphBuilder:
    """Builds semantic graphs from parser output."""
    
    def __init__(self, schema_path: Optional[str] = None):
        """Initialize graph builder with schema validation."""
        self.schema = self._load_schema(schema_path)
        self._resolution_cache: Dict[str, Optional[str]] = {}
        self._builtin_functions = self._load_builtin_functions()
    
    def _load_schema(self, schema_path: Optional[str]) -> Dict[str, Any]:
        """Load and validate graph schema."""
        if schema_path is None:
            # Use default schema path
            current_dir = os.path.dirname(__file__)
            schema_path = os.path.join(current_dir, '..', '..', 'configs', 'graph', 'schema.yaml')
        
        try:
            with open(schema_path, 'r') as f:
                schema = yaml.safe_load(f)
            logger.info(f"Loaded graph schema from {schema_path}")
            return schema
        except FileNotFoundError:
            logger.warning(f"Schema file not found: {schema_path}, using minimal schema")
            return self._get_minimal_schema()
    
    def _get_minimal_schema(self) -> Dict[str, Any]:
        """Get minimal schema when file is not available."""
        return {
            'schema': {
                'node_types': {
                    'file': {'required_properties': ['path', 'language', 'loc']},
                    'function': {'required_properties': ['name', 'qualified_name', 'line_start', 'line_end']},
                    'class': {'required_properties': ['name', 'qualified_name', 'line_start', 'line_end']},
                    'module': {'required_properties': ['name', 'qualified_name']},
                    'variable': {'required_properties': ['name', 'qualified_name']}
                },
                'edge_types': {
                    'contains': {'source_types': ['file', 'class'], 'target_types': ['function', 'class']},
                    'calls': {'source_types': ['function'], 'target_types': ['function']},
                    'inherits': {'source_types': ['class'], 'target_types': ['class']},
                    'imports': {'source_types': ['file'], 'target_types': ['module', 'function', 'class']}
                }
            }
        }
    
    def _load_builtin_functions(self) -> Set[str]:
        """Load set of builtin function names for different languages."""
        # This could be loaded from configuration files
        return {
            # Python builtins
            'print', 'len', 'str', 'int', 'float', 'bool', 'list', 'dict', 'set', 'tuple',
            'range', 'enumerate', 'zip', 'map', 'filter', 'sorted', 'reversed',
            'open', 'input', 'type', 'isinstance', 'hasattr', 'getattr', 'setattr',
            'min', 'max', 'sum', 'abs', 'round', 'pow',
            # Go builtins
            'make', 'new', 'append', 'copy', 'delete', 'len', 'cap',
            'panic', 'recover', 'close',
            # Java builtins (methods from Object, System, etc.)
            'toString', 'equals', 'hashCode', 'println', 'print'
        }
    
    def from_parser_output(self, parser_output: Dict[str, Any]) -> Graph:
        """Convert parser output to semantic graph."""
        graph = Graph()
        
        # Clear resolution cache for new file
        self._resolution_cache.clear()
        
        file_path = parser_output.get('file_path', 'unknown')
        language = parser_output.get('language', 'unknown')
        
        # Create file node
        file_node = self._create_file_node(parser_output)
        graph.add_node(file_node)
        
        # Create module nodes from imports
        module_nodes = self._create_module_nodes(parser_output)
        for module_node in module_nodes:
            graph.add_node(module_node)
        
        # Create function nodes
        function_nodes = self._create_function_nodes(parser_output, file_path)
        for func_node in function_nodes:
            graph.add_node(func_node)
            # Add contains edge: file -> function
            contains_edge = ContainsEdge(
                source=file_node.id,
                target=func_node.id,
                line_number=func_node.line_start
            )
            graph.add_edge(contains_edge)
        
        # Create class nodes
        class_nodes = self._create_class_nodes(parser_output, file_path)
        for class_node in class_nodes:
            graph.add_node(class_node)
            # Add contains edge: file -> class
            contains_edge = ContainsEdge(
                source=file_node.id,
                target=class_node.id,
                line_number=class_node.line_start
            )
            graph.add_edge(contains_edge)
        
        # Create call edges
        call_edges = self._create_call_edges(parser_output, function_nodes, file_path)
        for edge in call_edges:
            try:
                graph.add_edge(edge)
            except ValueError as e:
                logger.debug(f"Skipping call edge {edge.source} -> {edge.target}: {e}")
        
        # Create inheritance edges
        inheritance_edges = self._create_inheritance_edges(class_nodes, file_path)
        for edge in inheritance_edges:
            try:
                graph.add_edge(edge)
            except ValueError as e:
                logger.debug(f"Skipping inheritance edge {edge.source} -> {edge.target}: {e}")
        
        # Create import edges
        import_edges = self._create_import_edges(parser_output, file_node.id)
        for edge in import_edges:
            # Create target module node if it doesn't exist
            target_module_id = edge.target
            if not graph.has_node(target_module_id):
                module_name = target_module_id.replace('module:', '')
                module_node = ModuleNode(
                    id=target_module_id,
                    name=module_name.split('.')[-1],
                    qualified_name=module_name
                )
                graph.add_node(module_node)
            
            try:
                graph.add_edge(edge)
            except ValueError as e:
                logger.debug(f"Skipping import edge {edge.source} -> {edge.target}: {e}")
        
        logger.info(f"Built graph for {file_path}: {len(graph.nodes)} nodes, {len(graph.edges)} edges")
        return graph
    
    def _create_file_node(self, parser_output: Dict[str, Any]) -> FileNode:
        """Create file node from parser output."""
        file_path = parser_output.get('file_path', 'unknown')
        language = parser_output.get('language', 'unknown')
        
        # Calculate lines of code
        loc = 0
        if 'metrics' in parser_output:
            loc = parser_output['metrics'].get('loc', 0)
        elif 'source_code' in parser_output:
            loc = len(parser_output['source_code'].splitlines())
        
        file_id = create_node_id('file', file_path)
        
        return FileNode(
            id=file_id,
            path=file_path,
            language=language,
            loc=loc,
            encoding=parser_output.get('encoding', 'utf-8'),
            size_bytes=parser_output.get('size_bytes', 0)
        )
    
    def _create_module_nodes(self, parser_output: Dict[str, Any]) -> List[ModuleNode]:
        """Create module nodes from imports."""
        modules = []
        imports = parser_output.get('imports', [])
        
        for import_info in imports:
            module_name = import_info.get('module', import_info.get('name', ''))
            if not module_name:
                continue
            
            module_id = create_node_id('module', module_name)
            module_node = ModuleNode(
                id=module_id,
                name=module_name.split('.')[-1],
                qualified_name=module_name,
                import_type=import_info.get('type', 'import')
            )
            modules.append(module_node)
        
        return modules
    
    def _create_function_nodes(self, parser_output: Dict[str, Any], file_path: str) -> List[FunctionNode]:
        """Create function nodes from parser output."""
        functions = []
        func_data = parser_output.get('functions', [])
        
        for func in func_data:
            name = func.get('name', 'unknown')
            qualified_name = func.get('qualified_name', name)
            
            # Create unique ID
            func_id = create_node_id('function', qualified_name, file_path)
            
            func_node = FunctionNode(
                id=func_id,
                name=name,
                qualified_name=qualified_name,
                line_start=func.get('line_start', 0),
                line_end=func.get('line_end', 0),
                complexity=func.get('complexity'),
                params=func.get('parameters', []),
                return_type=func.get('return_type'),
                decorators=func.get('decorators', []),
                docstring=func.get('docstring'),
                is_async=func.get('is_async', False),
                is_generator=func.get('is_generator', False)
            )
            functions.append(func_node)
        
        return functions
    
    def _create_class_nodes(self, parser_output: Dict[str, Any], file_path: str) -> List[ClassNode]:
        """Create class nodes from parser output."""
        classes = []
        class_data = parser_output.get('classes', [])
        
        for cls in class_data:
            name = cls.get('name', 'unknown')
            qualified_name = cls.get('qualified_name', name)
            
            # Create unique ID
            class_id = create_node_id('class', qualified_name, file_path)
            
            class_node = ClassNode(
                id=class_id,
                name=name,
                qualified_name=qualified_name,
                line_start=cls.get('line_start', 0),
                line_end=cls.get('line_end', 0),
                base_classes=cls.get('base_classes', []),
                methods=[m.get('name', '') for m in cls.get('methods', [])],
                attributes=cls.get('attributes', []),
                decorators=cls.get('decorators', []),
                docstring=cls.get('docstring'),
                is_abstract=cls.get('is_abstract', False)
            )
            classes.append(class_node)
        
        return classes
    
    def _create_call_edges(self, parser_output: Dict[str, Any], 
                          function_nodes: List[FunctionNode], file_path: str) -> List[CallEdge]:
        """Create call edges from function call information."""
        call_edges = []
        
        # Build function lookup
        func_lookup = {func.name: func.id for func in function_nodes}
        
        for func in parser_output.get('functions', []):
            func_name = func.get('name', '')
            func_qualified_name = func.get('qualified_name', func_name)
            source_id = create_node_id('function', func_qualified_name, file_path)
            
            for call in func.get('calls', []):
                call_name = call.get('name', call.get('function', ''))
                if not call_name:
                    continue
                
                target_id = self._resolve_call_target(call_name, func_lookup, file_path)
                if target_id:
                    call_edge = CallEdge(
                        source=source_id,
                        target=target_id,
                        call_site=call.get('line', call.get('line_number')),
                        call_type=call.get('type', 'direct'),
                        arguments=call.get('arguments')
                    )
                    call_edges.append(call_edge)
        
        return call_edges
    
    def _create_inheritance_edges(self, class_nodes: List[ClassNode], file_path: str) -> List[InheritanceEdge]:
        """Create inheritance edges from class information."""
        inheritance_edges = []
        
        # Build class lookup
        class_lookup = {cls.name: cls.id for cls in class_nodes}
        
        for class_node in class_nodes:
            for base_class in class_node.base_classes:
                # Try to resolve base class
                if base_class in class_lookup:
                    target_id = class_lookup[base_class]
                else:
                    # Create ID for external base class
                    target_id = create_node_id('class', base_class, file_path)
                
                inheritance_edge = InheritanceEdge(
                    source=class_node.id,
                    target=target_id,
                    inheritance_type='single'  # Could be enhanced to detect multiple inheritance
                )
                inheritance_edges.append(inheritance_edge)
        
        return inheritance_edges
    
    def _create_import_edges(self, parser_output: Dict[str, Any], file_id: str) -> List[ImportEdge]:
        """Create import edges from import information."""
        import_edges = []
        
        for import_info in parser_output.get('imports', []):
            module_name = import_info.get('module', import_info.get('name', ''))
            if not module_name:
                continue
            
            target_id = create_node_id('module', module_name)
            
            import_edge = ImportEdge(
                source=file_id,
                target=target_id,
                import_type=import_info.get('type', 'import'),
                alias=import_info.get('alias'),
                line_number=import_info.get('line_number')
            )
            import_edges.append(import_edge)
        
        return import_edges
    
    def _resolve_call_target(self, call_name: str, func_lookup: Dict[str, str], 
                           file_path: str) -> Optional[str]:
        """Resolve call target to a qualified function ID."""
        # Check cache first
        cache_key = f"{file_path}:{call_name}"
        if cache_key in self._resolution_cache:
            return self._resolution_cache[cache_key]
        
        target_id = None
        
        # 1. Local function lookup
        if call_name in func_lookup:
            target_id = func_lookup[call_name]
        
        # 2. Builtin function
        elif call_name in self._builtin_functions:
            target_id = create_node_id('function', f"builtin.{call_name}")
        
        # 3. External function (create placeholder)
        else:
            # For now, create a placeholder ID
            # In a more sophisticated implementation, this would use import analysis
            target_id = create_node_id('function', f"external.{call_name}")
            logger.debug(f"Unresolved call target: {call_name}")
        
        # Cache the result
        self._resolution_cache[cache_key] = target_id
        return target_id
    
    def _find_in_local_scope(self, call_name: str, func_lookup: Dict[str, str]) -> Optional[str]:
        """Find function in local scope."""
        return func_lookup.get(call_name)
    
    def _find_in_imports(self, call_name: str) -> Optional[str]:
        """Find function in imported modules."""
        # This would require more sophisticated import analysis
        # For now, return None
        return None
    
    def _is_builtin(self, call_name: str) -> bool:
        """Check if function is a builtin."""
        return call_name in self._builtin_functions