"""
Query processor for executing graph queries.
"""

import logging
from typing import List, Dict, Any, Optional, Set
from dataclasses import dataclass

from .dsl import QueryAST, AttributeCondition, RelationCondition, LogicalOp
from ..storage.adapter import StorageAdapter
from ..models.node import Node
from ..models.edge import Edge

logger = logging.getLogger(__name__)


@dataclass
class ExecutionPlan:
    """Represents a query execution plan."""
    steps: List[Dict[str, Any]]
    estimated_cost: int
    use_index: bool = False


@dataclass
class QueryResult:
    """Represents query execution results."""
    nodes: List[Node]
    execution_time_ms: float
    total_count: int
    plan: Optional[ExecutionPlan] = None


class QueryProcessor:
    """Processes and executes graph queries."""
    
    def __init__(self, storage: StorageAdapter):
        """Initialize query processor with storage adapter."""
        self.storage = storage
    
    def execute(self, query_ast: QueryAST) -> QueryResult:
        """Execute a parsed query."""
        import time
        start_time = time.time()
        
        # Generate execution plan
        plan = self._generate_execution_plan(query_ast)
        
        # Execute the plan
        nodes = self._execute_plan(query_ast, plan)
        
        # Apply limit and offset
        total_count = len(nodes)
        if query_ast.offset:
            nodes = nodes[query_ast.offset:]
        if query_ast.limit:
            nodes = nodes[:query_ast.limit]
        
        execution_time = (time.time() - start_time) * 1000
        
        return QueryResult(
            nodes=nodes,
            execution_time_ms=execution_time,
            total_count=total_count,
            plan=plan
        )
    
    def _generate_execution_plan(self, query_ast: QueryAST) -> ExecutionPlan:
        """Generate execution plan for query."""
        steps = []
        estimated_cost = 0
        use_index = True
        
        # Step 1: Initial node scan
        if query_ast.where and self._has_attribute_filters(query_ast.where):
            # Use filtered scan
            steps.append({
                'type': 'filtered_scan',
                'node_type': query_ast.find.node_type,
                'filters': self._extract_attribute_filters(query_ast.where)
            })
            estimated_cost += 100  # Filtered scan cost
        else:
            # Full type scan
            steps.append({
                'type': 'type_scan',
                'node_type': query_ast.find.node_type
            })
            estimated_cost += 500  # Full scan cost
        
        # Step 2: Relation filtering
        if query_ast.where and self._has_relation_filters(query_ast.where):
            relation_filters = self._extract_relation_filters(query_ast.where)
            for rel_filter in relation_filters:
                steps.append({
                    'type': 'relation_filter',
                    'relation': rel_filter
                })
                estimated_cost += 200  # Relation traversal cost
        
        return ExecutionPlan(steps=steps, estimated_cost=estimated_cost, use_index=use_index)
    
    def _execute_plan(self, query_ast: QueryAST, plan: ExecutionPlan) -> List[Node]:
        """Execute the query plan."""
        nodes = []
        
        for step in plan.steps:
            if step['type'] == 'type_scan':
                nodes = self._execute_type_scan(step['node_type'])
            elif step['type'] == 'filtered_scan':
                nodes = self._execute_filtered_scan(step['node_type'], step['filters'])
            elif step['type'] == 'relation_filter':
                nodes = self._execute_relation_filter(nodes, step['relation'])
        
        # Apply any remaining WHERE conditions
        if query_ast.where:
            nodes = self._apply_where_clause(nodes, query_ast.where)
        
        return nodes
    
    def _execute_type_scan(self, node_type: str) -> List[Node]:
        """Execute a full type scan."""
        return self.storage.query_nodes(node_type, {}, limit=10000)
    
    def _execute_filtered_scan(self, node_type: str, filters: Dict[str, Any]) -> List[Node]:
        """Execute a filtered scan."""
        return self.storage.query_nodes(node_type, filters, limit=10000)
    
    def _execute_relation_filter(self, nodes: List[Node], relation: RelationCondition) -> List[Node]:
        """Filter nodes based on relation condition."""
        filtered_nodes = []
        
        relation_map = {
            'CALLING': 'calls',
            'INHERITS': 'inherits',
            'IMPORTS': 'imports',
            'CONTAINS': 'contains',
            'REFERENCES': 'references',
            'DEFINES': 'defines'
        }
        
        edge_type = relation_map.get(relation.relation_type)
        if not edge_type:
            logger.warning(f"Unknown relation type: {relation.relation_type}")
            return nodes
        
        for node in nodes:
            if self._node_has_relation(node, relation, edge_type):
                filtered_nodes.append(node)
        
        return filtered_nodes
    
    def _node_has_relation(self, node: Node, relation: RelationCondition, edge_type: str) -> bool:
        """Check if node has the specified relation."""
        try:
            if relation.direction == 'outgoing':
                edges = self.storage.get_edges(node.id, edge_type=edge_type)
                return any(self._target_matches(edge.target, relation.target) for edge in edges)
            elif relation.direction == 'incoming':
                # This is more expensive - would need to scan all edges
                # For now, we'll use a simplified approach
                return False
            else:
                # Both directions
                outgoing = self.storage.get_edges(node.id, edge_type=edge_type)
                return any(self._target_matches(edge.target, relation.target) for edge in outgoing)
        except Exception as e:
            logger.debug(f"Error checking relation for node {node.id}: {e}")
            return False
    
    def _target_matches(self, target_id: str, target_pattern: str) -> bool:
        """Check if target ID matches the pattern."""
        # Simple pattern matching - could be enhanced with regex
        if target_pattern == '*':
            return True
        
        # Check if target_id contains the pattern
        return target_pattern in target_id or target_id.endswith(target_pattern)
    
    def _apply_where_clause(self, nodes: List[Node], where_clause) -> List[Node]:
        """Apply WHERE clause conditions to nodes."""
        if not where_clause.conditions:
            return nodes
        
        filtered_nodes = []
        
        for node in nodes:
            if self._evaluate_conditions(node, where_clause.conditions):
                filtered_nodes.append(node)
        
        return filtered_nodes
    
    def _evaluate_conditions(self, node: Node, conditions: List) -> bool:
        """Evaluate conditions for a node."""
        if not conditions:
            return True
        
        # Simple evaluation - could be enhanced with proper boolean logic
        result = True
        current_op = 'AND'
        
        for condition in conditions:
            if isinstance(condition, LogicalOp):
                current_op = condition.operator
            elif isinstance(condition, AttributeCondition):
                condition_result = self._evaluate_attribute_condition(node, condition)
                if current_op == 'AND':
                    result = result and condition_result
                elif current_op == 'OR':
                    result = result or condition_result
            elif isinstance(condition, RelationCondition):
                # Relation conditions should have been handled earlier
                pass
        
        return result
    
    def _evaluate_attribute_condition(self, node: Node, condition: AttributeCondition) -> bool:
        """Evaluate attribute condition for a node."""
        node_value = node.properties.get(condition.attribute)
        
        if node_value is None:
            return False
        
        try:
            # Convert values for comparison
            if isinstance(condition.value, (int, float)):
                node_value = float(node_value) if isinstance(node_value, str) else node_value
            
            if condition.operator == '=':
                return node_value == condition.value
            elif condition.operator in ('!=', '<>'):
                return node_value != condition.value
            elif condition.operator == '>':
                return node_value > condition.value
            elif condition.operator == '<':
                return node_value < condition.value
            elif condition.operator == '>=':
                return node_value >= condition.value
            elif condition.operator == '<=':
                return node_value <= condition.value
            elif condition.operator == 'LIKE':
                return str(condition.value).lower() in str(node_value).lower()
            else:
                logger.warning(f"Unknown operator: {condition.operator}")
                return False
        except (ValueError, TypeError) as e:
            logger.debug(f"Error evaluating condition: {e}")
            return False
    
    def _has_attribute_filters(self, where_clause) -> bool:
        """Check if WHERE clause has attribute filters."""
        return any(isinstance(cond, AttributeCondition) for cond in where_clause.conditions)
    
    def _has_relation_filters(self, where_clause) -> bool:
        """Check if WHERE clause has relation filters."""
        return any(isinstance(cond, RelationCondition) for cond in where_clause.conditions)
    
    def _extract_attribute_filters(self, where_clause) -> Dict[str, Any]:
        """Extract attribute filters for storage query."""
        filters = {}
        
        for condition in where_clause.conditions:
            if isinstance(condition, AttributeCondition):
                if condition.operator == '=':
                    filters[condition.attribute] = condition.value
                elif condition.operator == '>':
                    filters[condition.attribute] = {'$gt': condition.value}
                elif condition.operator == '<':
                    filters[condition.attribute] = {'$lt': condition.value}
                elif condition.operator == '>=':
                    filters[condition.attribute] = {'$gte': condition.value}
                elif condition.operator == '<=':
                    filters[condition.attribute] = {'$lte': condition.value}
                elif condition.operator in ('!=', '<>'):
                    filters[condition.attribute] = {'$ne': condition.value}
        
        return filters
    
    def _extract_relation_filters(self, where_clause) -> List[RelationCondition]:
        """Extract relation filters."""
        return [cond for cond in where_clause.conditions if isinstance(cond, RelationCondition)]
    
    # Convenience methods for common queries
    
    def find_functions_calling(self, target_function: str, limit: int = 100) -> List[Node]:
        """Find all functions that call a specific function."""
        try:
            # Get all call edges to the target function
            all_functions = self.storage.query_nodes('function', {}, limit=10000)
            calling_functions = []
            
            for func in all_functions:
                edges = self.storage.get_edges(func.id, edge_type='calls')
                for edge in edges:
                    if self._target_matches(edge.target, target_function):
                        calling_functions.append(func)
                        break
            
            return calling_functions[:limit]
        except Exception as e:
            logger.error(f"Error finding functions calling {target_function}: {e}")
            return []
    
    def get_class_hierarchy(self, base_class: str, max_depth: int = 5) -> List[Node]:
        """Get class inheritance hierarchy."""
        try:
            hierarchy = []
            visited = set()
            queue = [(base_class, 0)]
            
            while queue:
                class_name, depth = queue.pop(0)
                
                if depth > max_depth or class_name in visited:
                    continue
                
                visited.add(class_name)
                
                # Find classes that inherit from this class
                all_classes = self.storage.query_nodes('class', {}, limit=10000)
                for cls in all_classes:
                    if cls.id not in visited:
                        edges = self.storage.get_edges(cls.id, edge_type='inherits')
                        for edge in edges:
                            if self._target_matches(edge.target, class_name):
                                hierarchy.append(cls)
                                queue.append((cls.get_qualified_name(), depth + 1))
            
            return hierarchy
        except Exception as e:
            logger.error(f"Error getting class hierarchy for {base_class}: {e}")
            return []
    
    def find_file_dependencies(self, module_name: str) -> List[Node]:
        """Find all files that import from a specific module."""
        try:
            importing_files = []
            all_files = self.storage.query_nodes('file', {}, limit=10000)
            
            for file_node in all_files:
                edges = self.storage.get_edges(file_node.id, edge_type='imports')
                for edge in edges:
                    if self._target_matches(edge.target, module_name):
                        importing_files.append(file_node)
                        break
            
            return importing_files
        except Exception as e:
            logger.error(f"Error finding file dependencies for {module_name}: {e}")
            return []
    
    def find_high_complexity_functions(self, threshold: int = 10) -> List[Node]:
        """Find functions with complexity above threshold."""
        try:
            filters = {'complexity': {'$gt': threshold}}
            return self.storage.query_nodes('function', filters, limit=1000)
        except Exception as e:
            logger.error(f"Error finding high complexity functions: {e}")
            return []
    
    def find_unused_functions(self) -> List[Node]:
        """Find functions that are never called."""
        try:
            all_functions = self.storage.query_nodes('function', {}, limit=10000)
            unused_functions = []
            
            # Get all call edges
            all_call_targets = set()
            for func in all_functions:
                edges = self.storage.get_edges(func.id, edge_type='calls')
                for edge in edges:
                    all_call_targets.add(edge.target)
            
            # Find functions not in call targets
            for func in all_functions:
                if func.id not in all_call_targets:
                    # Additional check: not a main function or entry point
                    if not func.name.startswith('main') and not func.name.startswith('__'):
                        unused_functions.append(func)
            
            return unused_functions
        except Exception as e:
            logger.error(f"Error finding unused functions: {e}")
            return []