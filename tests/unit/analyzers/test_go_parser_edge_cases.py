"""
Comprehensive test suite for Go parser edge cases
"""
import pytest
from codesage.analyzers.go_parser import GoParser


class TestGoParserEdgeCases:
    """Edge case tests for Go parser"""
    
    def setup_method(self):
        """Setup test fixtures"""
        self.parser = GoParser()
    
    def test_generic_functions(self):
        """Test generic function parsing with type constraints"""
        code = """
package main

import "constraints"

func Add[T constraints.Ordered](a, b T) T {
    return a + b
}

func Transform[T any, U any](input T, fn func(T) U) U {
    return fn(input)
}

type Numeric interface {
    ~int | ~float64
}

func Sum[T Numeric](values []T) T {
    var sum T
    for _, v := range values {
        sum += v
    }
    return sum
}
"""
        self.parser.parse(code)
        functions = self.parser.extract_functions()
        
        # Should extract 3 functions
        assert len(functions) >= 3
        
        func_dict = {f.name: f for f in functions}
        
        # Test Add function
        add_func = func_dict['Add']
        assert 'generic' in add_func.decorators
        assert hasattr(add_func, 'type_parameters')
        assert len(add_func.type_parameters) == 1
        assert add_func.type_parameters[0]['name'] == 'T'
        assert 'Ordered' in add_func.type_parameters[0]['constraint']
        
        # Test Transform function
        transform_func = func_dict['Transform']
        assert 'generic' in transform_func.decorators
        assert len(transform_func.type_parameters) == 2
        
        # Test Sum function
        sum_func = func_dict['Sum']
        assert 'generic' in sum_func.decorators
        assert len(sum_func.type_parameters) == 1
        assert sum_func.type_parameters[0]['name'] == 'T'
        assert 'Numeric' in sum_func.type_parameters[0]['constraint']
    
    def test_generic_structs_with_tags(self):
        """Test generic struct parsing with struct tags"""
        code = """
package main

type Container[T any] struct {
    Value T                `json:"value"`
    Items []T              `json:"items"`
    Meta  map[string]any   `json:"meta,omitempty"`
}

type Cache[K comparable, V any] struct {
    data map[K]V           `json:"-" db:"cache_data"`
    size int               `json:"size" validate:"min=0"`
}

func (c *Container[T]) Add(item T) {
    c.Items = append(c.Items, item)
}

func (c *Cache[K, V]) Set(key K, value V) {
    c.data[key] = value
}
"""
        self.parser.parse(code)
        structs = self.parser.extract_structs()
        functions = self.parser.extract_functions()
        
        # Should extract 2 structs
        assert len(structs) >= 2
        
        struct_dict = {s.name: s for s in structs}
        
        # Test Container struct
        container = struct_dict['Container']
        assert hasattr(container, 'type_parameters')
        assert len(container.type_parameters) == 1
        assert container.type_parameters[0]['name'] == 'T'
        
        # Check struct tags
        value_field = next(f for f in container.fields if f.name == 'Value')
        assert hasattr(value_field, 'struct_tag')
        assert 'json:"value"' in value_field.struct_tag
        
        # Test Cache struct
        cache = struct_dict['Cache']
        assert len(cache.type_parameters) == 2
        
        # Test methods
        func_dict = {f.name: f for f in functions}
        add_method = func_dict['Add']
        assert add_method.receiver is not None
        assert 'Container' in add_method.receiver
    
    def test_interface_with_type_parameters(self):
        """Test interface parsing with type parameters"""
        code = """
package main

type Processor[T any] interface {
    Process(T) T
    Validate(T) bool
}

type Comparable[T any] interface {
    Compare(T) int
    Equal(T) bool
}

type StringProcessor struct{}

func (sp StringProcessor) Process(s string) string {
    return s
}

func (sp StringProcessor) Validate(s string) bool {
    return len(s) > 0
}
"""
        self.parser.parse(code)
        interfaces = self.parser.extract_interfaces()
        
        # Should extract 2 interfaces
        assert len(interfaces) >= 2
        
        interface_dict = {i.name: i for i in interfaces}
        
        # Test Processor interface
        processor = interface_dict['Processor']
        assert processor.node_type == 'interface'
        assert len(processor.methods) >= 2
        
        # Test method signatures
        method_names = [m.name for m in processor.methods]
        assert 'Process' in method_names
        assert 'Validate' in method_names
    
    def test_method_receivers(self):
        """Test method receiver parsing"""
        code = """
package main

type User struct {
    Name string
    Age  int
}

func (u User) GetName() string {
    return u.Name
}

func (u *User) SetName(name string) {
    u.Name = name
}

func (u *User) IsAdult() bool {
    return u.Age >= 18
}
"""
        self.parser.parse(code)
        functions = self.parser.extract_functions()
        
        # Should extract 3 methods
        assert len(functions) == 3
        
        func_dict = {f.name: f for f in functions}
        
        # Test value receiver
        get_name = func_dict['GetName']
        assert get_name.receiver is not None
        assert 'User' in get_name.receiver
        assert '*' not in get_name.receiver  # Value receiver
        
        # Test pointer receivers
        set_name = func_dict['SetName']
        assert set_name.receiver is not None
        assert '*User' in set_name.receiver  # Pointer receiver
        
        is_adult = func_dict['IsAdult']
        assert is_adult.receiver is not None
        assert '*User' in is_adult.receiver  # Pointer receiver
    
    def test_embedded_fields(self):
        """Test embedded field parsing"""
        code = """
package main

type Person struct {
    Name string
    Age  int
}

type Employee struct {
    Person              // Embedded field
    *Company            // Embedded pointer field
    ID       string     `json:"id"`
    Salary   float64    `json:"salary"`
}

type Company struct {
    Name string
}
"""
        self.parser.parse(code)
        structs = self.parser.extract_structs()
        
        struct_dict = {s.name: s for s in structs}
        
        # Test Employee struct with embedded fields
        employee = struct_dict['Employee']
        field_names = [f.name for f in employee.fields]
        
        # Should have embedded fields
        assert 'Person' in field_names  # Embedded struct
        assert '*Company' in field_names  # Embedded pointer
        assert 'ID' in field_names  # Regular field
        assert 'Salary' in field_names  # Regular field
        
        # Check embedded field properties
        person_field = next(f for f in employee.fields if f.name == 'Person')
        assert person_field.kind == 'embedded_field'
        assert person_field.is_exported is True  # Person is exported
        
        company_field = next(f for f in employee.fields if f.name == '*Company')
        assert company_field.kind == 'embedded_field'
        assert company_field.is_exported is True  # Company is exported
    
    def test_complex_struct_tags(self):
        """Test complex struct tag parsing"""
        code = """
package main

type User struct {
    ID        int       `json:"id" db:"user_id" validate:"required"`
    Name      string    `json:"name" db:"full_name" validate:"required,min=2,max=50"`
    Email     string    `json:"email" db:"email_address" validate:"required,email"`
    CreatedAt time.Time `json:"created_at" db:"created_at"`
    Settings  UserSettings `json:"settings" db:"-"`
}

type UserSettings struct {
    Theme string `json:"theme" default:"light"`
    Lang  string `json:"language" default:"en"`
}
"""
        self.parser.parse(code)
        structs = self.parser.extract_structs()
        
        struct_dict = {s.name: s for s in structs}
        user = struct_dict['User']
        
        # Check complex tags
        id_field = next(f for f in user.fields if f.name == 'ID')
        assert hasattr(id_field, 'struct_tag')
        tag = id_field.struct_tag
        assert 'json:"id"' in tag
        assert 'db:"user_id"' in tag
        assert 'validate:"required"' in tag
        
        name_field = next(f for f in user.fields if f.name == 'Name')
        assert 'validate:"required,min=2,max=50"' in name_field.struct_tag
        
        settings_field = next(f for f in user.fields if f.name == 'Settings')
        assert 'db:"-"' in settings_field.struct_tag  # Excluded from DB
    
    def test_go_specific_features(self):
        """Test Go-specific features like goroutines and channels"""
        code = """
package main

func main() {
    ch := make(chan int, 10)
    
    go func() {
        ch <- 42
    }()
    
    go worker(ch)
    
    value := <-ch
    
    if err != nil {
        return
    }
}

func worker(ch chan int) {
    for value := range ch {
        go process(value)
    }
}

func process(value int) {
    // Process value
}
"""
        self.parser.parse(code)
        stats = self.parser.get_stats()
        
        # Should detect goroutines and channels
        assert stats['goroutines'] > 0
        assert stats['channels'] > 0
    
    def test_variadic_functions(self):
        """Test variadic function parsing"""
        code = """
package main

func Printf(format string, args ...interface{}) {
    // Implementation
}

func Sum(numbers ...int) int {
    total := 0
    for _, num := range numbers {
        total += num
    }
    return total
}

func Process[T any](items ...T) []T {
    result := make([]T, len(items))
    copy(result, items)
    return result
}
"""
        self.parser.parse(code)
        functions = self.parser.extract_functions()
        
        func_dict = {f.name: f for f in functions}
        
        # Test Printf function
        printf_func = func_dict['Printf']
        assert any('...interface{}' in param for param in printf_func.params)
        
        # Test Sum function
        sum_func = func_dict['Sum']
        assert any('...int' in param for param in sum_func.params)
        
        # Test generic variadic function
        process_func = func_dict['Process']
        assert 'generic' in process_func.decorators
        assert any('...T' in param for param in process_func.params)
    
    def test_function_types_and_closures(self):
        """Test function types and closure parsing"""
        code = """
package main

type Handler func(string) error
type Middleware func(Handler) Handler

func CreateHandler() Handler {
    return func(input string) error {
        return nil
    }
}

func WithLogging(next Handler) Handler {
    return func(input string) error {
        log.Printf("Processing: %s", input)
        return next(input)
    }
}

func Map[T, U any](slice []T, fn func(T) U) []U {
    result := make([]U, len(slice))
    for i, v := range slice {
        result[i] = fn(v)
    }
    return result
}
"""
        self.parser.parse(code)
        functions = self.parser.extract_functions()
        
        # Should extract the named functions (not the anonymous ones)
        func_names = [f.name for f in functions]
        assert 'CreateHandler' in func_names
        assert 'WithLogging' in func_names
        assert 'Map' in func_names
        
        # Test generic Map function
        func_dict = {f.name: f for f in functions}
        map_func = func_dict['Map']
        assert 'generic' in map_func.decorators
        assert len(map_func.type_parameters) == 2
    
    @pytest.mark.benchmark
    def test_parsing_performance(self, benchmark):
        """Test Go parsing performance"""
        # Generate a large Go file
        lines = ['package main', '']
        for i in range(50):
            lines.append(f"""
type Struct{i}[T any] struct {{
    Field1 T                `json:"field1"`
    Field2 string           `json:"field2"`
    Field3 int              `json:"field3"`
}}

func (s *Struct{i}[T]) Method{i}(param T) T {{
    if param != nil {{
        for j := 0; j < 10; j++ {{
            if j%2 == 0 {{
                continue
            }}
            return param
        }}
    }}
    return s.Field1
}}

func Function{i}[T constraints.Ordered](a, b T) T {{
    if a > b {{
        return a
    }}
    return b
}}
""")
        
        large_code = '\n'.join(lines)
        
        def parse_large_code():
            parser = GoParser()
            parser.parse(large_code)
            functions = parser.extract_functions()
            structs = parser.extract_structs()
            return functions, structs
        
        functions, structs = benchmark(parse_large_code)
        
        # Should extract many functions and structs
        assert len(functions) >= 100
        assert len(structs) >= 50
        
        # Performance should be reasonable
        assert benchmark.stats.mean < 0.5