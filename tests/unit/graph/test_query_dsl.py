"""
Unit tests for Query DSL parser and processor.
"""

import pytest
from unittest.mock import Mock, MagicMock

from codesage.graph.query.dsl import (
    QueryDSL, QuerySyntaxError, QueryAST, FindClause, WhereClause,
    AttributeCondition, RelationCondition, LogicalOp, parse_query
)
from codesage.graph.query.processor import QueryProcessor, QueryResult, ExecutionPlan
from codesage.graph.models.node import FunctionNode, ClassNode, FileNode
from codesage.graph.models.edge import CallEdge, InheritanceEdge
from codesage.graph.storage.adapter import StorageAdapter


class TestQueryDSL:
    """Test Query DSL parser."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.parser = QueryDSL()
    
    def test_simple_find_query(self):
        """Test parsing simple FIND query."""
        query = "FIND functions"
        ast = self.parser.parse(query)
        
        assert isinstance(ast, QueryAST)
        assert ast.find.node_type == "functions"
        assert ast.where is None
        assert ast.limit is None
    
    def test_find_with_alias(self):
        """Test FIND query with alias."""
        query = "FIND functions AS f"
        ast = self.parser.parse(query)
        
        assert ast.find.node_type == "functions"
        assert ast.find.alias == "f"
    
    def test_find_with_where_attribute(self):
        """Test FIND query with WHERE attribute condition."""
        query = "FIND functions WHERE complexity > 10"
        ast = self.parser.parse(query)
        
        assert ast.find.node_type == "functions"
        assert ast.where is not None
        assert len(ast.where.conditions) == 1
        
        condition = ast.where.conditions[0]
        assert isinstance(condition, AttributeCondition)
        assert condition.attribute == "complexity"
        assert condition.operator == ">"
        assert condition.value == 10
    
    def test_find_with_where_relation(self):
        """Test FIND query with WHERE relation condition."""
        query = "FIND functions WHERE CALLING 'target_func'"
        ast = self.parser.parse(query)
        
        assert ast.find.node_type == "functions"
        assert ast.where is not None
        assert len(ast.where.conditions) == 1
        
        condition = ast.where.conditions[0]
        assert isinstance(condition, RelationCondition)
        assert condition.relation_type == "CALLING"
        assert condition.target == "target_func"
        assert condition.direction == "outgoing"
    
    def test_find_with_complex_where(self):
        """Test FIND query with complex WHERE clause."""
        query = "FIND functions WHERE complexity > 5 AND CALLING 'helper'"
        ast = self.parser.parse(query)
        
        assert len(ast.where.conditions) == 3  # condition + AND + condition
        
        attr_condition = ast.where.conditions[0]
        assert isinstance(attr_condition, AttributeCondition)
        assert attr_condition.attribute == "complexity"
        assert attr_condition.value == 5
        
        logical_op = ast.where.conditions[1]
        assert isinstance(logical_op, LogicalOp)
        assert logical_op.operator == "AND"
        
        rel_condition = ast.where.conditions[2]
        assert isinstance(rel_condition, RelationCondition)
        assert rel_condition.relation_type == "CALLING"
        assert rel_condition.target == "helper"
    
    def test_find_with_limit(self):
        """Test FIND query with LIMIT."""
        query = "FIND functions LIMIT 50"
        ast = self.parser.parse(query)
        
        assert ast.find.node_type == "functions"
        assert ast.limit == 50
    
    def test_find_with_offset(self):
        """Test FIND query with OFFSET."""
        query = "FIND functions LIMIT 50 OFFSET 10"
        ast = self.parser.parse(query)
        
        assert ast.find.node_type == "functions"
        assert ast.limit == 50
        assert ast.offset == 10
    
    def test_various_operators(self):
        """Test various comparison operators."""
        test_cases = [
            ("complexity = 5", "=", 5),
            ("complexity != 10", "!=", 10),
            ("complexity >= 3", ">=", 3),
            ("complexity <= 15", "<=", 15),
            ("name = 'test'", "=", "test"),
        ]
        
        for query_part, expected_op, expected_value in test_cases:
            query = f"FIND functions WHERE {query_part}"
            ast = self.parser.parse(query)
            
            condition = ast.where.conditions[0]
            assert condition.operator == expected_op
            assert condition.value == expected_value
    
    def test_various_relations(self):
        """Test various relation types."""
        test_cases = [
            ("CALLING 'func'", "CALLING", "outgoing"),
            ("INHERITS 'BaseClass'", "INHERITS", "outgoing"),
            ("IMPORTS 'module'", "IMPORTS", "outgoing"),
            ("CONTAINS 'item'", "CONTAINS", "incoming"),
        ]
        
        for relation_part, expected_type, expected_direction in test_cases:
            query = f"FIND classes WHERE {relation_part}"
            ast = self.parser.parse(query)
            
            condition = ast.where.conditions[0]
            assert isinstance(condition, RelationCondition)
            assert condition.relation_type == expected_type
            assert condition.direction == expected_direction
    
    def test_tokenization(self):
        """Test query tokenization."""
        query = "FIND functions WHERE complexity > 10 AND name = 'test'"
        tokens = self.parser._tokenize(query)
        
        # Check some key tokens
        token_values = [t.value for t in tokens if t.value != '']
        assert "FIND" in token_values
        assert "functions" in token_values
        assert "WHERE" in token_values
        assert "complexity" in token_values
        assert ">" in token_values
        assert "10" in token_values
        assert "AND" in token_values
        assert "test" in token_values
    
    def test_syntax_errors(self):
        """Test various syntax errors."""
        invalid_queries = [
            "",  # Empty query
            "FIND",  # Missing node type
            "FIND functions WHERE",  # Incomplete WHERE
            "FIND functions WHERE complexity",  # Missing operator
            "FIND functions WHERE complexity >",  # Missing value
            "FIND functions WHERE CALLING",  # Missing target
            "INVALID functions",  # Invalid keyword
        ]
        
        for query in invalid_queries:
            with pytest.raises(QuerySyntaxError):
                self.parser.parse(query)
    
    def test_parse_query_convenience_function(self):
        """Test convenience parse_query function."""
        query = "FIND functions WHERE complexity > 5"
        ast = parse_query(query)
        
        assert isinstance(ast, QueryAST)
        assert ast.find.node_type == "functions"
    
    def test_validate_query_against_schema(self):
        """Test query validation against schema."""
        schema = {
            'schema': {
                'node_types': {
                    'function': {
                        'required_properties': ['name', 'qualified_name'],
                        'optional_properties': ['complexity', 'params']
                    }
                },
                'edge_types': {
                    'calls': {
                        'source_types': ['function'],
                        'target_types': ['function']
                    }
                }
            }
        }
        
        # Valid query
        query = "FIND function WHERE complexity > 5"
        ast = self.parser.parse(query)
        self.parser.validate(ast, schema)  # Should not raise
        
        # Invalid node type
        query = "FIND invalid_type WHERE complexity > 5"
        ast = self.parser.parse(query)
        with pytest.raises(QuerySyntaxError, match="Unknown node type"):
            self.parser.validate(ast, schema)


class TestQueryProcessor:
    """Test Query processor."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.mock_storage = Mock(spec=StorageAdapter)
        self.processor = QueryProcessor(self.mock_storage)
        
        # Create test nodes
        self.func1 = FunctionNode(
            id="func:func1",
            name="func1",
            qualified_name="module.func1",
            line_start=1,
            line_end=10,
            complexity=5
        )
        self.func2 = FunctionNode(
            id="func:func2",
            name="func2",
            qualified_name="module.func2",
            line_start=11,
            line_end=20,
            complexity=15
        )
        self.func3 = FunctionNode(
            id="func:func3",
            name="func3",
            qualified_name="module.func3",
            line_start=21,
            line_end=30,
            complexity=3
        )
    
    def test_execute_simple_query(self):
        """Test executing simple query."""
        # Mock storage response
        self.mock_storage.query_nodes.return_value = [self.func1, self.func2, self.func3]
        
        # Parse and execute query
        query = "FIND function"
        ast = parse_query(query)
        result = self.processor.execute(ast)
        
        assert isinstance(result, QueryResult)
        assert len(result.nodes) == 3
        assert result.total_count == 3
        assert result.execution_time_ms > 0
        
        # Verify storage was called correctly
        self.mock_storage.query_nodes.assert_called_once_with('function', {}, limit=10000)
    
    def test_execute_query_with_filters(self):
        """Test executing query with attribute filters."""
        # Mock storage response
        self.mock_storage.query_nodes.return_value = [self.func2]  # Only high complexity
        
        # Parse and execute query
        query = "FIND function WHERE complexity > 10"
        ast = parse_query(query)
        result = self.processor.execute(ast)
        
        assert len(result.nodes) == 1
        assert result.nodes[0].complexity == 15
        
        # Verify storage was called with filters
        expected_filters = {'complexity': {'$gt': 10}}
        self.mock_storage.query_nodes.assert_called_once_with('function', expected_filters, limit=10000)
    
    def test_execute_query_with_limit(self):
        """Test executing query with LIMIT."""
        # Mock storage response
        self.mock_storage.query_nodes.return_value = [self.func1, self.func2, self.func3]
        
        # Parse and execute query
        query = "FIND function LIMIT 2"
        ast = parse_query(query)
        result = self.processor.execute(ast)
        
        assert len(result.nodes) == 2
        assert result.total_count == 3  # Total before limit
    
    def test_execute_query_with_offset(self):
        """Test executing query with OFFSET."""
        # Mock storage response
        self.mock_storage.query_nodes.return_value = [self.func1, self.func2, self.func3]
        
        # Parse and execute query
        query = "FIND function OFFSET 1 LIMIT 2"
        ast = parse_query(query)
        result = self.processor.execute(ast)
        
        assert len(result.nodes) == 2
        assert result.nodes[0] == self.func2  # Should skip first node
    
    def test_execute_query_with_relation_filter(self):
        """Test executing query with relation filter."""
        # Mock storage responses
        self.mock_storage.query_nodes.return_value = [self.func1, self.func2]
        
        # Mock get_edges to return different results based on node_id
        def mock_get_edges(node_id, edge_type=None):
            if node_id == "func:func1":
                return [CallEdge("func:func1", "func:target_func")]
            else:
                return []  # func2 has no outgoing calls
        
        self.mock_storage.get_edges.side_effect = mock_get_edges
        
        # Parse and execute query
        query = "FIND function WHERE CALLING 'target_func'"
        ast = parse_query(query)
        result = self.processor.execute(ast)
        
        # Should filter to only func1 (which calls target_func)
        assert len(result.nodes) == 1
        assert result.nodes[0] == self.func1
    
    def test_generate_execution_plan(self):
        """Test execution plan generation."""
        # Simple query
        query = "FIND function"
        ast = parse_query(query)
        plan = self.processor._generate_execution_plan(ast)
        
        assert isinstance(plan, ExecutionPlan)
        assert len(plan.steps) >= 1
        assert plan.steps[0]['type'] == 'type_scan'
        assert plan.estimated_cost > 0
        
        # Query with filters
        query = "FIND function WHERE complexity > 10"
        ast = parse_query(query)
        plan = self.processor._generate_execution_plan(ast)
        
        assert plan.steps[0]['type'] == 'filtered_scan'
        assert 'filters' in plan.steps[0]
    
    def test_apply_attribute_filters(self):
        """Test applying attribute filters to nodes."""
        nodes = [self.func1, self.func2, self.func3]  # complexity: 5, 15, 3
        
        # Test greater than filter
        condition = AttributeCondition("complexity", ">", 10)
        filtered = [n for n in nodes if self.processor._evaluate_attribute_condition(n, condition)]
        assert len(filtered) == 1
        assert filtered[0] == self.func2
        
        # Test equality filter
        condition = AttributeCondition("complexity", "=", 5)
        filtered = [n for n in nodes if self.processor._evaluate_attribute_condition(n, condition)]
        assert len(filtered) == 1
        assert filtered[0] == self.func1
        
        # Test less than or equal filter
        condition = AttributeCondition("complexity", "<=", 5)
        filtered = [n for n in nodes if self.processor._evaluate_attribute_condition(n, condition)]
        assert len(filtered) == 2  # func1 and func3
    
    def test_convenience_methods(self):
        """Test convenience query methods."""
        # Test find_functions_calling
        self.mock_storage.query_nodes.return_value = [self.func1, self.func2]
        self.mock_storage.get_edges.side_effect = [
            [CallEdge("func:func1", "func:target")],  # func1 calls target
            []  # func2 doesn't call target
        ]
        
        result = self.processor.find_functions_calling("target")
        assert len(result) == 1
        assert result[0] == self.func1
        
        # Test find_high_complexity_functions
        self.mock_storage.query_nodes.return_value = [self.func2]
        result = self.processor.find_high_complexity_functions(threshold=10)
        assert len(result) == 1
        assert result[0] == self.func2
        
        # Verify storage was called with correct filters
        expected_filters = {'complexity': {'$gt': 10}}
        self.mock_storage.query_nodes.assert_called_with('function', expected_filters, limit=1000)
    
    def test_get_class_hierarchy(self):
        """Test class hierarchy query."""
        # Create test classes
        base_class = ClassNode(
            id="class:BaseClass",
            name="BaseClass",
            qualified_name="module.BaseClass",
            line_start=1,
            line_end=10
        )
        child_class = ClassNode(
            id="class:ChildClass",
            name="ChildClass",
            qualified_name="module.ChildClass",
            line_start=11,
            line_end=20,
            base_classes=["BaseClass"]
        )
        
        # Mock storage responses
        self.mock_storage.query_nodes.return_value = [child_class]
        self.mock_storage.get_edges.return_value = [
            InheritanceEdge("class:ChildClass", "class:BaseClass")
        ]
        
        result = self.processor.get_class_hierarchy("BaseClass")
        assert len(result) == 1
        assert result[0] == child_class
    
    def test_find_unused_functions(self):
        """Test finding unused functions."""
        # Mock storage responses
        self.mock_storage.query_nodes.return_value = [self.func1, self.func2, self.func3]
        
        # Mock edges - only func2 is called
        def mock_get_edges(source_id, edge_type=None):
            if source_id == "func:func1":
                return [CallEdge("func:func1", "func:func2")]
            return []
        
        self.mock_storage.get_edges.side_effect = mock_get_edges
        
        result = self.processor.find_unused_functions()
        
        # func1 and func3 should be unused (func2 is called by func1)
        unused_names = [f.name for f in result]
        assert "func1" in unused_names
        assert "func3" in unused_names
        assert "func2" not in unused_names
    
    def test_target_matching(self):
        """Test target pattern matching."""
        # Exact match
        assert self.processor._target_matches("func:module.target", "target")
        
        # Wildcard match
        assert self.processor._target_matches("func:any.function", "*")
        
        # Partial match
        assert self.processor._target_matches("func:module.helper_function", "helper")
        
        # No match
        assert not self.processor._target_matches("func:module.other", "target")


if __name__ == "__main__":
    pytest.main([__file__])