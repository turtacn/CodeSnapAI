package com.example.annotations;

import java.lang.annotation.*;
import java.util.List;
import javax.validation.constraints.*;
import org.springframework.web.bind.annotation.*;
import org.springframework.stereotype.*;

/**
 * Custom annotations
 */
@Target(ElementType.METHOD)
@Retention(RetentionPolicy.RUNTIME)
@interface Timed {
    String value() default "";
}

@Target(ElementType.TYPE)
@Retention(RetentionPolicy.RUNTIME)
@interface Entity {
    String table() default "";
}

@Target(ElementType.FIELD)
@Retention(RetentionPolicy.RUNTIME)
@interface Column {
    String name() default "";
    boolean nullable() default true;
}

/**
 * Nested annotations example
 */
@Target(ElementType.METHOD)
@Retention(RetentionPolicy.RUNTIME)
@interface ApiOperation {
    String value();
    String notes() default "";
    Class<?> response() default Void.class;
    String[] tags() default {};
    Authorization[] authorizations() default {};
}

@Target(ElementType.METHOD)
@Retention(RetentionPolicy.RUNTIME)
@interface Authorization {
    String value();
    AuthorizationScope[] scopes() default {};
}

@Target(ElementType.METHOD)
@Retention(RetentionPolicy.RUNTIME)
@interface AuthorizationScope {
    String scope();
    String description();
}

/**
 * Class with complex annotations
 */
@RestController
@RequestMapping("/api/users")
@CrossOrigin(origins = "http://localhost:3000")
@Validated
public class UserController {
    
    @GetMapping("/{id}")
    @ApiOperation(
        value = "Get user by ID",
        notes = "Returns a user based on ID",
        response = User.class,
        tags = {"user", "get"},
        authorizations = {
            @Authorization(
                value = "oauth2",
                scopes = {
                    @AuthorizationScope(scope = "read", description = "Read access"),
                    @AuthorizationScope(scope = "user", description = "User access")
                }
            )
        }
    )
    @Timed("user.get")
    public User getUser(@PathVariable @Min(1) Long id) {
        return userService.findById(id);
    }
    
    @PostMapping
    @ApiOperation(value = "Create user", response = User.class)
    @Timed("user.create")
    public User createUser(@RequestBody @Valid CreateUserRequest request) {
        return userService.create(request);
    }
    
    @PutMapping("/{id}")
    @Timed("user.update")
    public User updateUser(
        @PathVariable @Min(1) Long id,
        @RequestBody @Valid UpdateUserRequest request
    ) {
        return userService.update(id, request);
    }
    
    @DeleteMapping("/{id}")
    @ResponseStatus(HttpStatus.NO_CONTENT)
    @Timed("user.delete")
    public void deleteUser(@PathVariable @Min(1) Long id) {
        userService.delete(id);
    }
}

/**
 * Entity class with JPA annotations
 */
@Entity(table = "users")
@Table(name = "users")
@NamedQueries({
    @NamedQuery(
        name = "User.findByEmail",
        query = "SELECT u FROM User u WHERE u.email = :email"
    ),
    @NamedQuery(
        name = "User.findActiveUsers",
        query = "SELECT u FROM User u WHERE u.active = true"
    )
})
public class User {
    
    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    @Column(name = "id", nullable = false)
    private Long id;
    
    @Column(name = "username", nullable = false)
    @NotBlank(message = "Username cannot be blank")
    @Size(min = 3, max = 50, message = "Username must be between 3 and 50 characters")
    private String username;
    
    @Column(name = "email", nullable = false)
    @NotBlank(message = "Email cannot be blank")
    @Email(message = "Email must be valid")
    private String email;
    
    @Column(name = "age")
    @Min(value = 0, message = "Age must be non-negative")
    @Max(value = 150, message = "Age must be realistic")
    private Integer age;
    
    @Column(name = "active", nullable = false)
    private Boolean active = true;
    
    @OneToMany(mappedBy = "user", cascade = CascadeType.ALL, fetch = FetchType.LAZY)
    @JsonIgnore
    private List<Order> orders;
    
    // Constructors
    public User() {}
    
    public User(String username, String email) {
        this.username = username;
        this.email = email;
    }
    
    // Getters and setters with annotations
    @JsonProperty("id")
    public Long getId() {
        return id;
    }
    
    @JsonProperty("username")
    public String getUsername() {
        return username;
    }
    
    @JsonProperty("email")
    public String getEmail() {
        return email;
    }
    
    @JsonProperty("age")
    public Integer getAge() {
        return age;
    }
    
    @JsonProperty("active")
    public Boolean getActive() {
        return active;
    }
}

/**
 * Service class with Spring annotations
 */
@Service
@Transactional
@Slf4j
public class UserService {
    
    @Autowired
    private UserRepository userRepository;
    
    @Autowired
    private EmailService emailService;
    
    @Cacheable(value = "users", key = "#id")
    @Timed("user.service.findById")
    public User findById(Long id) {
        log.info("Finding user by id: {}", id);
        return userRepository.findById(id)
            .orElseThrow(() -> new UserNotFoundException("User not found: " + id));
    }
    
    @CacheEvict(value = "users", allEntries = true)
    @Timed("user.service.create")
    public User create(CreateUserRequest request) {
        log.info("Creating user: {}", request.getUsername());
        User user = new User(request.getUsername(), request.getEmail());
        user.setAge(request.getAge());
        User savedUser = userRepository.save(user);
        emailService.sendWelcomeEmail(savedUser.getEmail());
        return savedUser;
    }
    
    @CacheEvict(value = "users", key = "#id")
    @Timed("user.service.update")
    public User update(Long id, UpdateUserRequest request) {
        log.info("Updating user: {}", id);
        User user = findById(id);
        user.setUsername(request.getUsername());
        user.setEmail(request.getEmail());
        user.setAge(request.getAge());
        return userRepository.save(user);
    }
    
    @CacheEvict(value = "users", key = "#id")
    @Timed("user.service.delete")
    public void delete(Long id) {
        log.info("Deleting user: {}", id);
        User user = findById(id);
        userRepository.delete(user);
    }
}

/**
 * Configuration class with annotations
 */
@Configuration
@EnableCaching
@EnableScheduling
@Profile("production")
public class AppConfig {
    
    @Bean
    @Primary
    @ConditionalOnMissingBean
    public CacheManager cacheManager() {
        return new ConcurrentMapCacheManager("users", "orders");
    }
    
    @Bean
    @Scope("prototype")
    public EmailService emailService() {
        return new EmailServiceImpl();
    }
    
    @EventListener
    @Async
    public void handleUserCreated(UserCreatedEvent event) {
        // Handle user created event
    }
    
    @Scheduled(fixedRate = 60000)
    @Timed("cache.cleanup")
    public void cleanupCache() {
        // Cleanup cache periodically
    }
}

/**
 * Exception class with annotations
 */
@ResponseStatus(HttpStatus.NOT_FOUND)
public class UserNotFoundException extends RuntimeException {
    
    public UserNotFoundException(String message) {
        super(message);
    }
    
    public UserNotFoundException(String message, Throwable cause) {
        super(message, cause);
    }
}