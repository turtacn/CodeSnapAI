# Analyzer Development Guide

## Overview

This guide covers the development and testing of CodeSage analyzers, focusing on the Phase 1 stabilization improvements implemented for Python, Go, and Java parsers.

## Architecture

### Parser Factory

The `parser_factory.py` module provides a unified interface for creating language-specific parsers:

```python
from codesage.analyzers.parser_factory import create_parser

# Create a parser for a specific language
parser = create_parser('python')  # or 'go', 'java'
parser.parse(source_code)
functions = parser.extract_functions()
```

### Base Parser

All language parsers inherit from `BaseParser` which provides common functionality:

- Tree-sitter integration
- AST traversal utilities
- Error handling
- Performance monitoring

## Language-Specific Features

### Python Parser Enhancements

#### Nested Async Function Support

The Python parser now correctly handles nested async functions with proper parent scope tracking:

```python
async def outer():
    async def inner():  # Correctly tracked as nested in 'outer'
        pass
    return inner
```

**Implementation Details:**
- Recursive function extraction with scope stack
- Parent scope attribution for nested functions
- Proper async/await detection

#### Python 3.10+ Match Statement Support

Enhanced complexity calculation for match statements:

```python
def process_data(data):
    match data:
        case int() if data > 0:  # Each case adds to complexity
            return "positive"
        case int() if data < 0:
            return "negative"
        case _:
            return "unknown"
```

**Complexity Calculation:**
- Base complexity: 1
- Each case clause: +1
- Guard conditions: +1 each
- Logical operators (and/or): +1 each

#### Error Recovery

Robust error handling for syntax errors:

```python
def valid_function():
    return "valid"

def broken_function(
    # Missing closing parenthesis - syntax error
    param1: str

def another_valid_function():  # Still parsed correctly
    return "also valid"
```

**Features:**
- Partial AST extraction on syntax errors
- Graceful degradation
- Warning logging for parsing issues

### Go Parser Enhancements

#### Generic Type Support (Go 1.18+)

Full support for generic functions and structs:

```go
func Add[T constraints.Ordered](a, b T) T {
    return a + b
}

type Container[T any] struct {
    Value T
    Items []T
}
```

**Extracted Information:**
- Type parameter names
- Type constraints
- Generic decorators
- Constraint validation

#### Struct Tags

Enhanced struct tag extraction:

```go
type User struct {
    ID   int    `json:"id" db:"user_id" validate:"required"`
    Name string `json:"name" db:"full_name" validate:"required,min=2"`
}
```

**Features:**
- Complete tag preservation
- Multiple tag format support
- Tag-based semantic analysis

#### Method Receivers

Proper method receiver parsing:

```go
func (u *User) SetName(name string) {  // Pointer receiver
    u.Name = name
}

func (u User) GetName() string {       // Value receiver
    return u.Name
}
```

### Java Parser Enhancements

#### Record Class Support

Full support for Java 14+ record classes:

```java
public record Person(String name, int age) {
    public Person {  // Compact constructor
        if (name == null) throw new IllegalArgumentException();
    }
    
    public boolean isAdult() {
        return age >= 18;
    }
}
```

**Features:**
- Record component extraction
- Compact constructor detection
- Record method identification

#### Enhanced Annotation Parsing

Improved nested annotation support:

```java
@ApiOperation(
    value = "Get user",
    authorizations = {
        @Authorization(
            value = "oauth2",
            scopes = {@AuthorizationScope(scope = "read")}
        )
    }
)
public User getUser(@PathVariable Long id) {
    return userService.findById(id);
}
```

**Features:**
- Nested annotation extraction
- Annotation parameter parsing
- Semantic tag generation from annotations

#### Lambda Expression Filtering

Proper filtering of lambda expressions from function extraction:

```java
items.stream()
    .filter(item -> item.length() > 1)  // Not extracted as function
    .map(item -> item.toUpperCase())    // Not extracted as function
    .forEach(System.out::println);
```

## Testing Framework

### Test Structure

```
tests/
├── unit/analyzers/
│   ├── test_python_parser_comprehensive.py
│   ├── test_go_parser_edge_cases.py
│   ├── test_java_parser_advanced.py
│   └── test_ground_truth_validation.py
├── performance/
│   └── test_analyzer_performance.py
└── fixtures/analyzer-validation-set/
    ├── python/
    ├── go/
    ├── java/
    └── ground-truth/
```

### Test Categories

#### Unit Tests

Comprehensive unit tests for each parser:

- **Python**: Nested async functions, match statements, error recovery
- **Go**: Generic constraints, struct tags, method receivers
- **Java**: Record classes, nested annotations, lambda filtering

#### Performance Tests

Benchmarking for parsing speed and memory usage:

```python
@pytest.mark.benchmark
def test_python_parsing_speed_1000_loc(self, benchmark):
    code = generate_python_code(1000)
    result = benchmark(parse_python_code, code)
    assert benchmark.stats.mean < 0.5  # < 500ms
```

#### Ground Truth Validation

Accuracy validation against manually curated test cases:

```python
def test_python_nested_async_functions_accuracy(self):
    expected = load_ground_truth("complex_nested_async.py")
    actual = parse_and_extract(code)
    validate_accuracy(expected, actual)
```

### Test Configuration

The `.codesage/test-config.yaml` file defines:

- Coverage thresholds (95% minimum)
- Performance requirements (500ms for 1000 LOC)
- Accuracy targets (95% minimum)
- Test fixture specifications

### Running Tests

```bash
# Run all analyzer tests with coverage
pytest tests/unit/analyzers/ --cov=codesage/analyzers --cov-fail-under=95

# Run performance benchmarks
pytest tests/performance/ --benchmark-only

# Run ground truth validation
pytest tests/unit/analyzers/test_ground_truth_validation.py

# Run specific language tests
pytest tests/unit/analyzers/test_python_parser_comprehensive.py -v
```

## Performance Requirements

### Parsing Speed

- **Target**: Parse 1000 lines of code in < 500ms
- **Measurement**: Average time across multiple runs
- **Optimization**: Tree-sitter query optimization, caching

### Memory Usage

- **Target**: < 200MB peak memory for 10,000 LOC
- **Measurement**: Peak memory usage during parsing
- **Optimization**: Efficient AST traversal, garbage collection

### Accuracy

- **Target**: > 95% accuracy against ground truth
- **Measurement**: Function/class/import detection accuracy
- **Validation**: Manual verification of complex test cases

## Continuous Integration

### GitHub Actions Workflow

The `.github/workflows/analyzer-tests.yml` workflow:

1. **Test Matrix**: Python 3.10, 3.11, 3.12
2. **Coverage**: 95% minimum with HTML reports
3. **Performance**: Benchmark validation
4. **Quality**: Code style and lint checks
5. **Documentation**: Automated test report generation

### Quality Gates

- All tests must pass
- Coverage must be ≥ 95%
- Performance benchmarks must meet targets
- Code quality checks must pass
- Ground truth validation must achieve ≥ 95% accuracy

## Development Workflow

### Adding New Features

1. **Design**: Define the feature requirements
2. **Implementation**: Add parser logic
3. **Testing**: Create comprehensive tests
4. **Validation**: Add ground truth test cases
5. **Documentation**: Update this guide
6. **Performance**: Verify performance impact

### Bug Fixes

1. **Reproduction**: Create failing test case
2. **Fix**: Implement the fix
3. **Validation**: Ensure test passes
4. **Regression**: Run full test suite
5. **Performance**: Verify no performance degradation

### Performance Optimization

1. **Profiling**: Identify bottlenecks
2. **Optimization**: Implement improvements
3. **Benchmarking**: Measure performance gains
4. **Validation**: Ensure accuracy maintained
5. **Documentation**: Update performance metrics

## Best Practices

### Parser Development

- Use Tree-sitter queries for efficient AST traversal
- Implement error recovery for robust parsing
- Cache expensive operations
- Validate against real-world code samples

### Testing

- Write tests before implementing features (TDD)
- Use property-based testing for edge cases
- Benchmark performance regularly
- Maintain comprehensive ground truth dataset

### Code Quality

- Follow language-specific conventions
- Use type hints and documentation
- Implement proper error handling
- Optimize for readability and maintainability

## Troubleshooting

### Common Issues

#### Parsing Errors

- Check Tree-sitter grammar compatibility
- Verify source code encoding
- Review error recovery logic

#### Performance Issues

- Profile with `cProfile` or similar tools
- Check for inefficient AST traversal
- Optimize Tree-sitter queries

#### Test Failures

- Review ground truth expectations
- Check for language version compatibility
- Verify test fixture integrity

### Debugging Tools

- Tree-sitter playground for query testing
- Python debugger for step-through debugging
- Memory profilers for memory usage analysis
- Benchmark tools for performance analysis

## Future Enhancements

### Planned Features

- **Python**: Pattern matching optimization, walrus operator support
- **Go**: Workspace module support, build constraint parsing
- **Java**: Virtual threads, pattern matching for switch

### Performance Targets

- **Speed**: 1000 LOC in < 250ms (50% improvement)
- **Memory**: < 100MB for 10,000 LOC (50% reduction)
- **Accuracy**: > 98% ground truth validation

### Extensibility

- Plugin architecture for custom analyzers
- Language-agnostic semantic analysis
- Real-time parsing for IDE integration