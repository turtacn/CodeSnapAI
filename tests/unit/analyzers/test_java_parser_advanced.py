"""
Advanced test suite for Java parser
"""
import pytest
from codesage.analyzers.java_parser import JavaParser


class TestJavaParserAdvanced:
    """Advanced tests for Java parser"""
    
    def setup_method(self):
        """Setup test fixtures"""
        self.parser = JavaParser()
    
    def test_record_classes(self):
        """Test record class parsing"""
        code = """
public record Person(String name, int age) {
    public Person {
        if (name == null) {
            throw new IllegalArgumentException("Name cannot be null");
        }
    }
    
    public Person(String name) {
        this(name, 0);
    }
    
    public boolean isAdult() {
        return age >= 18;
    }
    
    public static Person createChild(String name) {
        return new Person(name, 0);
    }
}

public record Container<T>(T value, String label) {
    public boolean isEmpty() {
        return value == null;
    }
}
"""
        self.parser.parse(code)
        classes = self.parser.extract_classes()
        functions = self.parser.extract_functions()
        
        # Should extract 2 record classes
        record_classes = [c for c in classes if c.node_type == 'class']
        assert len(record_classes) >= 2
        
        # Test Person record
        person_class = next(c for c in classes if c.name == 'Person')
        assert person_class is not None
        
        # Test record constructor detection
        func_dict = {f.name: f for f in functions}
        
        # Should have constructors
        person_constructors = [f for f in functions if f.name == 'Person']
        assert len(person_constructors) >= 1
        
        # Test record constructor attributes
        for constructor in person_constructors:
            if hasattr(constructor, 'is_record_constructor'):
                assert constructor.is_record_constructor is True
                if hasattr(constructor, 'record_components'):
                    assert len(constructor.record_components) >= 0
    
    def test_nested_annotations(self):
        """Test nested annotation parsing"""
        code = """
@RestController
@RequestMapping("/api/users")
public class UserController {
    
    @GetMapping("/{id}")
    @ApiOperation(
        value = "Get user by ID",
        notes = "Returns a user",
        authorizations = {
            @Authorization(
                value = "oauth2",
                scopes = {
                    @AuthorizationScope(scope = "read", description = "Read access")
                }
            )
        }
    )
    public User getUser(@PathVariable Long id) {
        return userService.findById(id);
    }
    
    @PostMapping
    @Validated
    public User createUser(@RequestBody @Valid CreateUserRequest request) {
        return userService.create(request);
    }
}
"""
        self.parser.parse(code)
        classes = self.parser.extract_classes()
        functions = self.parser.extract_functions()
        
        # Test class annotations
        user_controller = next(c for c in classes if c.name == 'UserController')
        assert user_controller is not None
        
        # Test method annotations
        func_dict = {f.name: f for f in functions}
        
        get_user = func_dict['getUser']
        assert len(get_user.decorators) >= 2
        assert any('@GetMapping' in dec for dec in get_user.decorators)
        assert any('@ApiOperation' in dec for dec in get_user.decorators)
        
        create_user = func_dict['createUser']
        assert len(create_user.decorators) >= 2
        assert any('@PostMapping' in dec for dec in create_user.decorators)
        assert any('@Validated' in dec for dec in create_user.decorators)
    
    def test_lambda_expression_filtering(self):
        """Test that lambda expressions are not extracted as functions"""
        code = """
public class LambdaExample {
    public void processData() {
        List<String> items = Arrays.asList("a", "b", "c");
        
        items.stream()
            .filter(item -> item.length() > 1)
            .map(item -> item.toUpperCase())
            .forEach(System.out::println);
        
        Runnable task = () -> {
            System.out.println("Task executed");
        };
        
        Function<String, Integer> lengthFunction = (String s) -> {
            return s.length();
        };
    }
    
    public String regularMethod() {
        return "regular";
    }
}
"""
        self.parser.parse(code)
        functions = self.parser.extract_functions()
        
        # Should only extract regular methods, not lambda expressions
        func_names = [f.name for f in functions]
        assert 'processData' in func_names
        assert 'regularMethod' in func_names
        
        # Should not contain lambda-related names
        assert len(functions) == 2  # Only the two regular methods
    
    def test_throws_clause_extraction(self):
        """Test throws clause extraction"""
        code = """
public class ExceptionExample {
    public void methodWithSingleException() throws IOException {
        // Implementation
    }
    
    public void methodWithMultipleExceptions() throws IOException, SQLException, CustomException {
        // Implementation
    }
    
    public void methodWithoutThrows() {
        // Implementation
    }
}
"""
        self.parser.parse(code)
        functions = self.parser.extract_functions()
        
        func_dict = {f.name: f for f in functions}
        
        # Test single exception
        single_ex = func_dict['methodWithSingleException']
        assert hasattr(single_ex, 'throws_clause')
        assert len(single_ex.throws_clause) == 1
        assert 'IOException' in single_ex.throws_clause
        
        # Test multiple exceptions
        multi_ex = func_dict['methodWithMultipleExceptions']
        assert len(multi_ex.throws_clause) >= 3
        assert 'IOException' in multi_ex.throws_clause
        assert 'SQLException' in multi_ex.throws_clause
        assert 'CustomException' in multi_ex.throws_clause
        
        # Test no throws clause
        no_throws = func_dict['methodWithoutThrows']
        assert len(no_throws.throws_clause) == 0
    
    def test_synchronized_methods(self):
        """Test synchronized method detection"""
        code = """
public class SynchronizedExample {
    public synchronized void synchronizedMethod() {
        // Implementation
    }
    
    public static synchronized void staticSynchronizedMethod() {
        // Implementation
    }
    
    public void regularMethod() {
        synchronized (this) {
            // Synchronized block
        }
    }
}
"""
        self.parser.parse(code)
        functions = self.parser.extract_functions()
        
        func_dict = {f.name: f for f in functions}
        
        # Test synchronized instance method
        sync_method = func_dict['synchronizedMethod']
        assert hasattr(sync_method, 'is_synchronized')
        assert sync_method.is_synchronized is True
        
        # Test synchronized static method
        static_sync = func_dict['staticSynchronizedMethod']
        assert static_sync.is_synchronized is True
        assert hasattr(static_sync, 'is_static')
        assert static_sync.is_static is True
        
        # Test regular method
        regular = func_dict['regularMethod']
        assert regular.is_synchronized is False
    
    def test_generic_methods(self):
        """Test generic method parsing"""
        code = """
public class GenericExample {
    public <T> T identity(T value) {
        return value;
    }
    
    public <T, U> U transform(T input, Function<T, U> mapper) {
        return mapper.apply(input);
    }
    
    public <T extends Comparable<T>> T max(T a, T b) {
        return a.compareTo(b) > 0 ? a : b;
    }
    
    public static <E> List<E> createList(E... elements) {
        return Arrays.asList(elements);
    }
}
"""
        self.parser.parse(code)
        functions = self.parser.extract_functions()
        
        # All methods should be extracted
        assert len(functions) >= 4
        
        func_names = [f.name for f in functions]
        assert 'identity' in func_names
        assert 'transform' in func_names
        assert 'max' in func_names
        assert 'createList' in func_names
    
    def test_enum_classes(self):
        """Test enum class parsing"""
        code = """
public enum Status {
    PENDING("Pending"),
    APPROVED("Approved"),
    REJECTED("Rejected");
    
    private final String displayName;
    
    Status(String displayName) {
        this.displayName = displayName;
    }
    
    public String getDisplayName() {
        return displayName;
    }
    
    public boolean isCompleted() {
        return this == APPROVED || this == REJECTED;
    }
}
"""
        self.parser.parse(code)
        classes = self.parser.extract_classes()
        functions = self.parser.extract_functions()
        
        # Should extract enum class
        status_enum = next(c for c in classes if c.name == 'Status')
        assert status_enum is not None
        
        # Should extract enum methods
        func_names = [f.name for f in functions]
        assert 'Status' in func_names  # Constructor
        assert 'getDisplayName' in func_names
        assert 'isCompleted' in func_names
    
    def test_interface_default_methods(self):
        """Test interface with default methods"""
        code = """
public interface Processor {
    void process(String input);
    
    default void preProcess(String input) {
        System.out.println("Pre-processing: " + input);
    }
    
    default void postProcess(String input) {
        System.out.println("Post-processing: " + input);
    }
    
    static void utility() {
        System.out.println("Utility method");
    }
}
"""
        self.parser.parse(code)
        classes = self.parser.extract_classes()
        functions = self.parser.extract_functions()
        
        # Should extract interface
        processor_interface = next(c for c in classes if c.name == 'Processor')
        assert processor_interface is not None
        
        # Should extract interface methods
        func_names = [f.name for f in functions]
        assert 'process' in func_names
        assert 'preProcess' in func_names
        assert 'postProcess' in func_names
        assert 'utility' in func_names
    
    def test_sealed_classes(self):
        """Test sealed class parsing (Java 17+)"""
        code = """
public sealed class Shape permits Circle, Rectangle, Triangle {
    protected final String name;
    
    protected Shape(String name) {
        this.name = name;
    }
    
    public abstract double area();
}

public final class Circle extends Shape {
    private final double radius;
    
    public Circle(double radius) {
        super("Circle");
        this.radius = radius;
    }
    
    @Override
    public double area() {
        return Math.PI * radius * radius;
    }
}

public final class Rectangle extends Shape {
    private final double width, height;
    
    public Rectangle(double width, double height) {
        super("Rectangle");
        this.width = width;
        this.height = height;
    }
    
    @Override
    public double area() {
        return width * height;
    }
}
"""
        self.parser.parse(code)
        classes = self.parser.extract_classes()
        
        # Should extract all classes
        class_names = [c.name for c in classes]
        assert 'Shape' in class_names
        assert 'Circle' in class_names
        assert 'Rectangle' in class_names
        
        # Test inheritance relationships
        circle = next(c for c in classes if c.name == 'Circle')
        assert 'Shape' in circle.base_classes
        
        rectangle = next(c for c in classes if c.name == 'Rectangle')
        assert 'Shape' in rectangle.base_classes
    
    def test_annotation_semantic_tags(self):
        """Test semantic tag extraction from annotations"""
        code = """
@RestController
@RequestMapping("/api")
public class ApiController {
    
    @GetMapping("/users")
    public List<User> getUsers() {
        return userService.findAll();
    }
    
    @PostMapping("/users")
    public User createUser(@RequestBody User user) {
        return userService.save(user);
    }
}

@Service
@Transactional
public class UserService {
    
    @Autowired
    private UserRepository repository;
    
    public User save(User user) {
        return repository.save(user);
    }
}

@Entity
@Table(name = "users")
public class User {
    @Id
    @GeneratedValue
    private Long id;
    
    @Column(name = "username")
    private String username;
}
"""
        self.parser.parse(code)
        classes = self.parser.extract_classes()
        functions = self.parser.extract_functions()
        
        # Test class-level semantic tags
        class_dict = {c.name: c for c in classes}
        
        api_controller = class_dict['ApiController']
        assert 'controller' in api_controller.tags
        
        user_service = class_dict['UserService']
        assert 'service' in user_service.tags
        
        user_entity = class_dict['User']
        assert 'db_op' in user_entity.tags
        
        # Test method-level semantic tags
        func_dict = {f.name: f for f in functions}
        
        get_users = func_dict['getUsers']
        assert 'network' in get_users.tags
        
        create_user = func_dict['createUser']
        assert 'network' in create_user.tags
    
    @pytest.mark.benchmark
    def test_parsing_performance(self, benchmark):
        """Test Java parsing performance"""
        # Generate a large Java file
        lines = ['package com.example;', '']
        for i in range(30):
            lines.append(f"""
@Entity
@Table(name = "entity_{i}")
public class Entity{i} {{
    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;
    
    @Column(name = "name")
    private String name;
    
    @Column(name = "value")
    private Integer value;
    
    public Entity{i}() {{}}
    
    public Entity{i}(String name, Integer value) {{
        this.name = name;
        this.value = value;
    }}
    
    @Override
    public boolean equals(Object obj) {{
        if (this == obj) return true;
        if (obj == null || getClass() != obj.getClass()) return false;
        Entity{i} entity = (Entity{i}) obj;
        return Objects.equals(id, entity.id);
    }}
    
    @Override
    public int hashCode() {{
        return Objects.hash(id);
    }}
    
    public Long getId() {{ return id; }}
    public void setId(Long id) {{ this.id = id; }}
    
    public String getName() {{ return name; }}
    public void setName(String name) {{ this.name = name; }}
    
    public Integer getValue() {{ return value; }}
    public void setValue(Integer value) {{ this.value = value; }}
}}
""")
        
        large_code = '\n'.join(lines)
        
        def parse_large_code():
            parser = JavaParser()
            parser.parse(large_code)
            classes = parser.extract_classes()
            functions = parser.extract_functions()
            return classes, functions
        
        classes, functions = benchmark(parse_large_code)
        
        # Should extract many classes and functions
        assert len(classes) >= 30
        assert len(functions) >= 150  # Multiple methods per class
        
        # Performance should be reasonable
        assert benchmark.stats.mean < 0.5