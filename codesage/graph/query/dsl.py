"""
Query DSL parser for semantic graph queries.
"""

import re
import logging
from typing import List, Dict, Any, Optional, Union
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class QuerySyntaxError(Exception):
    """Raised when query syntax is invalid."""
    pass


class TokenType(Enum):
    """Token types for query parsing."""
    KEYWORD = "KEYWORD"
    IDENTIFIER = "IDENTIFIER"
    STRING = "STRING"
    NUMBER = "NUMBER"
    OPERATOR = "OPERATOR"
    LPAREN = "LPAREN"
    RPAREN = "RPAREN"
    EOF = "EOF"


@dataclass
class Token:
    """Represents a token in the query."""
    type: TokenType
    value: str
    position: int = 0


@dataclass
class FindClause:
    """Represents a FIND clause."""
    node_type: str
    alias: Optional[str] = None


@dataclass
class AttributeCondition:
    """Represents an attribute condition (e.g., complexity > 10)."""
    attribute: str
    operator: str
    value: Union[str, int, float]


@dataclass
class RelationCondition:
    """Represents a relation condition (e.g., CALLING 'foo')."""
    relation_type: str
    target: str
    direction: str = 'outgoing'  # 'outgoing', 'incoming', 'both'


@dataclass
class LogicalOp:
    """Represents a logical operator (AND, OR)."""
    operator: str


@dataclass
class WhereClause:
    """Represents a WHERE clause with conditions."""
    conditions: List[Union[AttributeCondition, RelationCondition, LogicalOp]]


@dataclass
class QueryAST:
    """Abstract syntax tree for a query."""
    find: FindClause
    where: Optional[WhereClause] = None
    limit: Optional[int] = None
    offset: Optional[int] = None


class QueryDSL:
    """Parser for graph query DSL."""
    
    KEYWORDS = {
        'FIND', 'WHERE', 'AND', 'OR', 'NOT', 'AS', 'CALLING', 'INHERITS', 
        'IMPORTS', 'CONTAINS', 'REFERENCES', 'DEFINES', 'LIMIT', 'OFFSET',
        'DEPTH', 'EXISTS'
    }
    
    OPERATORS = {
        '=', '!=', '<>', '>', '<', '>=', '<=', 'LIKE', 'IN'
    }
    
    def __init__(self):
        self.tokens: List[Token] = []
        self.position = 0
    
    def parse(self, query_str: str) -> QueryAST:
        """Parse query string into AST."""
        self.tokens = self._tokenize(query_str)
        self.position = 0
        
        if not self.tokens or self.tokens[0].type == TokenType.EOF:
            raise QuerySyntaxError("Empty query")
        
        return self._parse_query()
    
    def _tokenize(self, query_str: str) -> List[Token]:
        """Tokenize query string."""
        token_patterns = [
            (TokenType.STRING, r"'([^']*)'"),
            (TokenType.NUMBER, r'\d+(\.\d+)?'),
            (TokenType.OPERATOR, r'>=|<=|!=|<>|[><=]'),
            (TokenType.IDENTIFIER, r'[a-zA-Z_][a-zA-Z0-9_]*'),
            (TokenType.LPAREN, r'\('),
            (TokenType.RPAREN, r'\)'),
        ]
        
        # Combine all patterns
        pattern = '|'.join(f'(?P<{name.value}>{pattern})' for name, pattern in token_patterns)
        pattern += r'|(?P<SKIP>\s+)|(?P<MISMATCH>.)'
        
        tokens = []
        position = 0
        
        for match in re.finditer(pattern, query_str):
            token_type = match.lastgroup
            value = match.group()
            
            if token_type == 'SKIP':
                continue
            elif token_type == 'MISMATCH':
                raise QuerySyntaxError(f"Unexpected character '{value}' at position {match.start()}")
            
            # Convert token type
            if token_type == 'STRING':
                # Remove quotes - extract content from the appropriate group
                # Find the group that contains the string content
                for i in range(1, len(match.groups()) + 1):
                    try:
                        group_val = match.group(i)
                        if group_val and not group_val.startswith("'"):
                            value = group_val
                            break
                    except IndexError:
                        continue
                else:
                    # Fallback: strip quotes manually
                    value = match.group().strip("'\"")
                tokens.append(Token(TokenType.STRING, value, position))
            elif token_type == 'NUMBER':
                tokens.append(Token(TokenType.NUMBER, value, position))
            elif token_type == 'OPERATOR':
                tokens.append(Token(TokenType.OPERATOR, value, position))
            elif token_type == 'IDENTIFIER':
                # Check if it's a keyword
                if value.upper() in self.KEYWORDS:
                    tokens.append(Token(TokenType.KEYWORD, value.upper(), position))
                else:
                    tokens.append(Token(TokenType.IDENTIFIER, value, position))
            elif token_type == 'LPAREN':
                tokens.append(Token(TokenType.LPAREN, value, position))
            elif token_type == 'RPAREN':
                tokens.append(Token(TokenType.RPAREN, value, position))
            
            position = match.end()
        
        tokens.append(Token(TokenType.EOF, '', position))
        return tokens
    
    def _parse_query(self) -> QueryAST:
        """Parse complete query."""
        # Parse FIND clause
        find_clause = self._parse_find_clause()
        
        # Parse optional WHERE clause
        where_clause = None
        if self._current_token().type == TokenType.KEYWORD and self._current_token().value == 'WHERE':
            self._consume_token()  # consume WHERE
            where_clause = self._parse_where_clause()
        
        # Parse optional LIMIT clause
        limit = None
        if self._current_token().type == TokenType.KEYWORD and self._current_token().value == 'LIMIT':
            self._consume_token()  # consume LIMIT
            if self._current_token().type != TokenType.NUMBER:
                raise QuerySyntaxError("Expected number after LIMIT")
            limit = int(self._current_token().value)
            self._consume_token()
        
        # Parse optional OFFSET clause
        offset = None
        if self._current_token().type == TokenType.KEYWORD and self._current_token().value == 'OFFSET':
            self._consume_token()  # consume OFFSET
            if self._current_token().type != TokenType.NUMBER:
                raise QuerySyntaxError("Expected number after OFFSET")
            offset = int(self._current_token().value)
            self._consume_token()
        
        return QueryAST(find=find_clause, where=where_clause, limit=limit, offset=offset)
    
    def _parse_find_clause(self) -> FindClause:
        """Parse FIND clause."""
        if self._current_token().type != TokenType.KEYWORD or self._current_token().value != 'FIND':
            raise QuerySyntaxError("Expected FIND keyword")
        
        self._consume_token()  # consume FIND
        
        if self._current_token().type != TokenType.IDENTIFIER:
            raise QuerySyntaxError("Expected node type after FIND")
        
        node_type = self._current_token().value
        self._consume_token()
        
        # Optional alias (AS alias)
        alias = None
        if (self._current_token().type == TokenType.KEYWORD and 
            self._current_token().value == 'AS'):
            self._consume_token()  # consume AS
            if self._current_token().type != TokenType.IDENTIFIER:
                raise QuerySyntaxError("Expected alias after AS")
            alias = self._current_token().value
            self._consume_token()
        
        return FindClause(node_type=node_type, alias=alias)
    
    def _parse_where_clause(self) -> WhereClause:
        """Parse WHERE clause."""
        conditions = []
        
        while (self._current_token().type != TokenType.EOF and
               self._current_token().type != TokenType.KEYWORD or
               self._current_token().value not in ('LIMIT', 'OFFSET')):
            
            condition = self._parse_condition()
            conditions.append(condition)
            
            # Check for logical operators
            if (self._current_token().type == TokenType.KEYWORD and
                self._current_token().value in ('AND', 'OR')):
                logical_op = LogicalOp(self._current_token().value)
                conditions.append(logical_op)
                self._consume_token()
            else:
                break
        
        return WhereClause(conditions=conditions)
    
    def _parse_condition(self) -> Union[AttributeCondition, RelationCondition]:
        """Parse a single condition."""
        if self._current_token().type == TokenType.KEYWORD:
            # Relation condition (CALLING, INHERITS, etc.)
            return self._parse_relation_condition()
        elif self._current_token().type == TokenType.IDENTIFIER:
            # Attribute condition (complexity > 10)
            return self._parse_attribute_condition()
        else:
            raise QuerySyntaxError(f"Unexpected token: {self._current_token().value}")
    
    def _parse_attribute_condition(self) -> AttributeCondition:
        """Parse attribute condition."""
        if self._current_token().type != TokenType.IDENTIFIER:
            raise QuerySyntaxError("Expected attribute name")
        
        attribute = self._current_token().value
        self._consume_token()
        
        if self._current_token().type != TokenType.OPERATOR:
            raise QuerySyntaxError("Expected operator after attribute")
        
        operator = self._current_token().value
        self._consume_token()
        
        # Parse value
        if self._current_token().type == TokenType.NUMBER:
            value = float(self._current_token().value) if '.' in self._current_token().value else int(self._current_token().value)
        elif self._current_token().type == TokenType.STRING:
            # String values already have quotes stripped during tokenization
            value = self._current_token().value
        elif self._current_token().type == TokenType.IDENTIFIER:
            value = self._current_token().value
        else:
            raise QuerySyntaxError("Expected value after operator")
        
        self._consume_token()
        
        return AttributeCondition(attribute=attribute, operator=operator, value=value)
    
    def _parse_relation_condition(self) -> RelationCondition:
        """Parse relation condition."""
        if self._current_token().type != TokenType.KEYWORD:
            raise QuerySyntaxError("Expected relation keyword")
        
        relation_type = self._current_token().value
        self._consume_token()
        
        if self._current_token().type != TokenType.STRING:
            raise QuerySyntaxError(f"Expected string target after {relation_type}")
        
        # String values already have quotes stripped during tokenization
        target = self._current_token().value
        self._consume_token()
        
        # Determine direction based on relation type
        direction = 'outgoing'
        if relation_type in ('INHERITS', 'IMPORTS'):
            direction = 'outgoing'
        elif relation_type == 'CONTAINS':
            direction = 'incoming'  # Things contained by this node
        
        return RelationCondition(relation_type=relation_type, target=target, direction=direction)
    
    def _current_token(self) -> Token:
        """Get current token."""
        if self.position >= len(self.tokens):
            return Token(TokenType.EOF, '', self.position)
        return self.tokens[self.position]
    
    def _consume_token(self) -> Token:
        """Consume and return current token."""
        token = self._current_token()
        self.position += 1
        return token
    
    def validate(self, query_ast: QueryAST, schema: Dict[str, Any]) -> None:
        """Validate query AST against schema."""
        # Validate node type
        node_types = schema.get('schema', {}).get('node_types', {})
        if query_ast.find.node_type not in node_types:
            raise QuerySyntaxError(f"Unknown node type: {query_ast.find.node_type}")
        
        # Validate WHERE clause conditions
        if query_ast.where:
            for condition in query_ast.where.conditions:
                if isinstance(condition, AttributeCondition):
                    self._validate_attribute_condition(condition, query_ast.find.node_type, schema)
                elif isinstance(condition, RelationCondition):
                    self._validate_relation_condition(condition, schema)
    
    def _validate_attribute_condition(self, condition: AttributeCondition, 
                                    node_type: str, schema: Dict[str, Any]) -> None:
        """Validate attribute condition against schema."""
        node_schema = schema.get('schema', {}).get('node_types', {}).get(node_type, {})
        required_props = node_schema.get('required_properties', [])
        optional_props = node_schema.get('optional_properties', [])
        all_props = required_props + optional_props
        
        if condition.attribute not in all_props:
            logger.warning(f"Unknown attribute '{condition.attribute}' for node type '{node_type}'")
    
    def _validate_relation_condition(self, condition: RelationCondition, 
                                   schema: Dict[str, Any]) -> None:
        """Validate relation condition against schema."""
        edge_types = schema.get('schema', {}).get('edge_types', {})
        relation_map = {
            'CALLING': 'calls',
            'INHERITS': 'inherits',
            'IMPORTS': 'imports',
            'CONTAINS': 'contains',
            'REFERENCES': 'references',
            'DEFINES': 'defines'
        }
        
        edge_type = relation_map.get(condition.relation_type)
        if edge_type and edge_type not in edge_types:
            raise QuerySyntaxError(f"Unknown relation type: {condition.relation_type}")


def parse_query(query_str: str) -> QueryAST:
    """Convenience function to parse a query string."""
    parser = QueryDSL()
    return parser.parse(query_str)