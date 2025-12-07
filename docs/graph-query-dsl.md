# Graph Query DSL Documentation

## Overview

The CodeSnapAI Graph Query DSL (Domain Specific Language) provides a SQL-like syntax for querying semantic graphs. It enables developers to efficiently search for code patterns, analyze dependencies, and explore code relationships across large codebases.

## Syntax Reference

### Basic Query Structure

```bnf
Query ::= FindClause [WhereClause] [LimitClause] [OffsetClause]
```

### Find Clause

The `FIND` clause specifies the type of nodes to search for:

```sql
FIND <node_type> [AS <alias>]
```

**Supported Node Types:**
- `function` - Functions and methods
- `class` - Class definitions
- `file` - Source code files
- `module` - Modules and packages
- `variable` - Variable definitions

**Examples:**
```sql
FIND function
FIND class AS c
FIND file
```

### Where Clause

The `WHERE` clause filters results based on node properties or relationships:

```sql
WHERE <condition> [AND|OR <condition>]...
```

#### Attribute Conditions

Filter nodes by their properties:

```sql
<attribute> <operator> <value>
```

**Supported Operators:**
- `=` - Equals
- `!=` or `<>` - Not equals
- `>` - Greater than
- `<` - Less than
- `>=` - Greater than or equal
- `<=` - Less than or equal
- `LIKE` - Pattern matching

**Examples:**
```sql
WHERE complexity > 10
WHERE name = 'main'
WHERE loc >= 100 AND loc <= 500
WHERE qualified_name LIKE 'test_%'
```

#### Relationship Conditions

Filter nodes based on their relationships to other nodes:

```sql
<relation_type> '<target>'
```

**Supported Relation Types:**
- `CALLING` - Function calls another function
- `INHERITS` - Class inherits from another class
- `IMPORTS` - File/module imports another module
- `CONTAINS` - Container holds another element
- `REFERENCES` - References another symbol
- `DEFINES` - Defines a symbol

**Examples:**
```sql
WHERE CALLING 'helper_function'
WHERE INHERITS 'BaseClass'
WHERE IMPORTS 'numpy'
WHERE CONTAINS 'method_name'
```

### Limit and Offset

Control the number of results returned:

```sql
LIMIT <number>
OFFSET <number>
```

**Examples:**
```sql
LIMIT 50
OFFSET 10 LIMIT 20
```

## Query Examples

### Basic Queries

#### Find All Functions
```sql
FIND function
```

#### Find High Complexity Functions
```sql
FIND function WHERE complexity > 15
```

#### Find Large Files
```sql
FIND file WHERE loc > 1000
```

### Relationship Queries

#### Find Functions Calling a Specific Function
```sql
FIND function WHERE CALLING 'database_connect'
```

#### Find Classes Inheriting from a Base Class
```sql
FIND class WHERE INHERITS 'BaseModel'
```

#### Find Files Importing a Module
```sql
FIND file WHERE IMPORTS 'requests'
```

### Complex Queries

#### Find Medium Complexity Functions with Specific Patterns
```sql
FIND function WHERE complexity > 5 AND complexity < 20 AND name LIKE 'process_%'
```

#### Find Classes with Many Methods
```sql
FIND class WHERE method_count > 10 AND INHERITS 'BaseClass'
```

#### Find Unused Functions (Functions Not Called by Others)
```sql
FIND function WHERE NOT EXISTS (
    FIND function WHERE CALLING current.name
)
```

### Pagination Examples

#### Get First 50 Functions
```sql
FIND function LIMIT 50
```

#### Get Next 50 Functions
```sql
FIND function OFFSET 50 LIMIT 50
```

## Node Properties Reference

### Function Node Properties

| Property | Type | Description |
|----------|------|-------------|
| `name` | string | Function name |
| `qualified_name` | string | Fully qualified name |
| `complexity` | integer | Cyclomatic complexity |
| `line_start` | integer | Starting line number |
| `line_end` | integer | Ending line number |
| `params` | array | Parameter list |
| `return_type` | string | Return type annotation |
| `is_async` | boolean | Whether function is async |
| `is_generator` | boolean | Whether function is a generator |

### Class Node Properties

| Property | Type | Description |
|----------|------|-------------|
| `name` | string | Class name |
| `qualified_name` | string | Fully qualified name |
| `line_start` | integer | Starting line number |
| `line_end` | integer | Ending line number |
| `base_classes` | array | List of base classes |
| `methods` | array | List of method names |
| `method_count` | integer | Number of methods |
| `is_abstract` | boolean | Whether class is abstract |

### File Node Properties

| Property | Type | Description |
|----------|------|-------------|
| `path` | string | File path |
| `language` | string | Programming language |
| `loc` | integer | Lines of code |
| `encoding` | string | File encoding |
| `last_modified` | timestamp | Last modification time |

### Module Node Properties

| Property | Type | Description |
|----------|------|-------------|
| `name` | string | Module name |
| `qualified_name` | string | Fully qualified name |
| `version` | string | Module version |
| `exports` | array | Exported symbols |

## Advanced Features

### Subqueries

Use subqueries to create complex filtering conditions:

```sql
FIND function WHERE complexity > (
    SELECT AVG(complexity) FROM function
)
```

### Aggregation Functions

Perform aggregations on query results:

```sql
SELECT COUNT(*) FROM function WHERE complexity > 10
SELECT AVG(complexity) FROM function GROUP BY file_path
```

### Graph Traversal

Traverse relationships with depth control:

```sql
FIND function WHERE CALLING 'target' DEPTH 3
```

This finds all functions that call 'target' within 3 levels of indirection.

## Performance Considerations

### Index Usage

The query processor automatically uses indexes when available:

- **Node type indexes** - Efficient filtering by node type
- **Property indexes** - Fast property-based filtering
- **Relationship indexes** - Optimized relationship traversal

### Query Optimization

The query processor applies several optimizations:

1. **Predicate Pushdown** - Filters applied as early as possible
2. **Index Selection** - Chooses optimal indexes for conditions
3. **Cost Estimation** - Selects execution plan with lowest estimated cost

### Best Practices

1. **Use specific filters** - Add WHERE clauses to reduce result sets
2. **Limit results** - Use LIMIT to avoid large result sets
3. **Index-friendly conditions** - Use equality and range conditions when possible
4. **Avoid complex patterns** - Simple patterns perform better than complex ones

## Error Handling

### Syntax Errors

```sql
-- Invalid: Missing node type
FIND WHERE complexity > 10
-- Error: Expected node type after FIND

-- Invalid: Unknown operator
FIND function WHERE complexity ~= 10
-- Error: Unknown operator '~='
```

### Semantic Errors

```sql
-- Invalid: Unknown node type
FIND unknown_type
-- Error: Unknown node type 'unknown_type'

-- Invalid: Unknown property
FIND function WHERE unknown_property > 10
-- Warning: Unknown property 'unknown_property' for node type 'function'
```

### Runtime Errors

```sql
-- Invalid: Type mismatch
FIND function WHERE complexity > 'high'
-- Error: Cannot compare integer with string
```

## Integration Examples

### Python API

```python
from codesage.graph.query import QueryProcessor, parse_query

# Initialize processor with storage adapter
processor = QueryProcessor(storage_adapter)

# Parse and execute query
query_ast = parse_query("FIND function WHERE complexity > 10")
result = processor.execute(query_ast)

# Process results
for node in result.nodes:
    print(f"Function: {node.name}, Complexity: {node.complexity}")
```

### CLI Usage

```bash
# Execute query via CLI
codesage query "FIND function WHERE complexity > 10"

# Save results to file
codesage query "FIND class WHERE INHERITS 'BaseModel'" --output results.json

# Format output
codesage query "FIND file WHERE loc > 1000" --format table
```

### REST API

```bash
# Execute query via REST API
curl -X POST http://localhost:8000/api/query \
  -H "Content-Type: application/json" \
  -d '{"query": "FIND function WHERE complexity > 10"}'
```

## Future Extensions

### Planned Features

1. **Regular Expressions** - Pattern matching with regex
2. **Temporal Queries** - Query historical graph states
3. **Graph Algorithms** - Built-in graph analysis functions
4. **Custom Functions** - User-defined query functions
5. **Query Caching** - Automatic caching of frequent queries

### Experimental Features

1. **Natural Language Queries** - Convert English to DSL
2. **Visual Query Builder** - Drag-and-drop query construction
3. **Query Suggestions** - Auto-complete and suggestions
4. **Performance Profiling** - Query execution analysis