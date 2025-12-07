package com.example.records;

import java.time.LocalDateTime;
import java.util.List;
import java.util.Objects;

/**
 * Simple record example
 */
public record Person(String name, int age) {
    // Compact constructor with validation
    public Person {
        if (name == null || name.isBlank()) {
            throw new IllegalArgumentException("Name cannot be null or blank");
        }
        if (age < 0) {
            throw new IllegalArgumentException("Age cannot be negative");
        }
    }
    
    // Additional constructor
    public Person(String name) {
        this(name, 0);
    }
    
    // Instance method
    public boolean isAdult() {
        return age >= 18;
    }
    
    // Static method
    public static Person createChild(String name) {
        return new Person(name, 0);
    }
}

/**
 * Record with generic type parameters
 */
public record Container<T>(T value, String label) {
    public Container {
        Objects.requireNonNull(value, "Value cannot be null");
        Objects.requireNonNull(label, "Label cannot be null");
    }
    
    public boolean isEmpty() {
        return value == null;
    }
}

/**
 * Record implementing interface
 */
public interface Identifiable {
    String getId();
}

public record User(String id, String username, String email) implements Identifiable {
    public User {
        if (id == null || id.isBlank()) {
            throw new IllegalArgumentException("ID cannot be null or blank");
        }
        if (username == null || username.isBlank()) {
            throw new IllegalArgumentException("Username cannot be null or blank");
        }
        if (email == null || !email.contains("@")) {
            throw new IllegalArgumentException("Invalid email address");
        }
    }
    
    @Override
    public String getId() {
        return id;
    }
    
    public String getDisplayName() {
        return username + " (" + email + ")";
    }
}

/**
 * Nested record
 */
public class OrderService {
    public record OrderItem(String productId, int quantity, double price) {
        public OrderItem {
            if (productId == null || productId.isBlank()) {
                throw new IllegalArgumentException("Product ID cannot be null or blank");
            }
            if (quantity <= 0) {
                throw new IllegalArgumentException("Quantity must be positive");
            }
            if (price < 0) {
                throw new IllegalArgumentException("Price cannot be negative");
            }
        }
        
        public double getTotalPrice() {
            return quantity * price;
        }
    }
    
    public record Order(String orderId, List<OrderItem> items, LocalDateTime createdAt) {
        public Order {
            Objects.requireNonNull(orderId, "Order ID cannot be null");
            Objects.requireNonNull(items, "Items cannot be null");
            Objects.requireNonNull(createdAt, "Created date cannot be null");
            if (items.isEmpty()) {
                throw new IllegalArgumentException("Order must have at least one item");
            }
        }
        
        public double getTotalAmount() {
            return items.stream()
                    .mapToDouble(OrderItem::getTotalPrice)
                    .sum();
        }
        
        public int getTotalItems() {
            return items.stream()
                    .mapToInt(OrderItem::quantity)
                    .sum();
        }
    }
    
    public Order createOrder(String orderId, List<OrderItem> items) {
        return new Order(orderId, items, LocalDateTime.now());
    }
}

/**
 * Record with annotations
 */
import com.fasterxml.jackson.annotation.JsonProperty;

public record ApiResponse<T>(
    @JsonProperty("data") T data,
    @JsonProperty("status") int status,
    @JsonProperty("message") String message,
    @JsonProperty("timestamp") LocalDateTime timestamp
) {
    public ApiResponse {
        Objects.requireNonNull(timestamp, "Timestamp cannot be null");
    }
    
    public static <T> ApiResponse<T> success(T data) {
        return new ApiResponse<>(data, 200, "Success", LocalDateTime.now());
    }
    
    public static <T> ApiResponse<T> error(String message) {
        return new ApiResponse<>(null, 500, message, LocalDateTime.now());
    }
    
    public boolean isSuccess() {
        return status >= 200 && status < 300;
    }
}

/**
 * Record with sealed interface
 */
public sealed interface Result<T> permits Success, Error {
    record Success<T>(T value) implements Result<T> {}
    record Error<T>(String message, Throwable cause) implements Result<T> {}
    
    default boolean isSuccess() {
        return this instanceof Success;
    }
    
    default boolean isError() {
        return this instanceof Error;
    }
}

/**
 * Main class demonstrating record usage
 */
public class RecordDemo {
    public static void main(String[] args) {
        // Simple record usage
        Person person = new Person("John Doe", 30);
        System.out.println("Person: " + person);
        System.out.println("Is adult: " + person.isAdult());
        
        // Generic record usage
        Container<String> stringContainer = new Container<>("Hello", "greeting");
        Container<Integer> intContainer = new Container<>(42, "answer");
        
        // Record with interface
        User user = new User("123", "johndoe", "john@example.com");
        System.out.println("User ID: " + user.getId());
        System.out.println("Display name: " + user.getDisplayName());
        
        // Nested records
        OrderService service = new OrderService();
        List<OrderService.OrderItem> items = List.of(
            new OrderService.OrderItem("PROD1", 2, 10.99),
            new OrderService.OrderItem("PROD2", 1, 25.50)
        );
        OrderService.Order order = service.createOrder("ORD001", items);
        System.out.println("Order total: $" + order.getTotalAmount());
        
        // API response record
        ApiResponse<String> response = ApiResponse.success("Operation completed");
        System.out.println("Response: " + response);
        
        // Result record
        Result<String> successResult = new Result.Success<>("Success value");
        Result<String> errorResult = new Result.Error<>("Error message", new RuntimeException());
        System.out.println("Success: " + successResult.isSuccess());
        System.out.println("Error: " + errorResult.isError());
    }
}