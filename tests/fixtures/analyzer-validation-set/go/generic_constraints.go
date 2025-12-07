package main

import (
	"fmt"
	"constraints"
)

// Generic function with type constraints
func Add[T constraints.Ordered](a, b T) T {
	return a + b
}

// Generic function with multiple type parameters
func Transform[T any, U any](input T, fn func(T) U) U {
	return fn(input)
}

// Generic function with custom constraint
type Numeric interface {
	~int | ~int8 | ~int16 | ~int32 | ~int64 |
		~uint | ~uint8 | ~uint16 | ~uint32 | ~uint64 |
		~float32 | ~float64
}

func Sum[T Numeric](values []T) T {
	var sum T
	for _, v := range values {
		sum += v
	}
	return sum
}

// Generic struct with type parameters
type Container[T any] struct {
	Value T
	Items []T
}

func (c *Container[T]) Add(item T) {
	c.Items = append(c.Items, item)
}

func (c *Container[T]) Get() T {
	return c.Value
}

// Generic struct with multiple constraints
type Cache[K comparable, V any] struct {
	data map[K]V
}

func NewCache[K comparable, V any]() *Cache[K, V] {
	return &Cache[K, V]{
		data: make(map[K]V),
	}
}

func (c *Cache[K, V]) Set(key K, value V) {
	c.data[key] = value
}

func (c *Cache[K, V]) Get(key K) (V, bool) {
	value, exists := c.data[key]
	return value, exists
}

// Generic interface
type Processor[T any] interface {
	Process(T) T
	Validate(T) bool
}

// Implementation of generic interface
type StringProcessor struct{}

func (sp StringProcessor) Process(s string) string {
	return fmt.Sprintf("processed: %s", s)
}

func (sp StringProcessor) Validate(s string) bool {
	return len(s) > 0
}

// Generic function with complex constraints
type Serializable interface {
	Serialize() []byte
	Deserialize([]byte) error
}

func SaveToFile[T Serializable](item T, filename string) error {
	data := item.Serialize()
	// Save data to file logic here
	fmt.Printf("Saving %d bytes to %s\n", len(data), filename)
	return nil
}

// Nested generic types
type Result[T any, E error] struct {
	Value T
	Error E
}

func (r Result[T, E]) IsOk() bool {
	return r.Error == nil
}

func (r Result[T, E]) Unwrap() T {
	if r.Error != nil {
		panic(r.Error)
	}
	return r.Value
}

func main() {
	// Usage examples
	result := Add(5, 3)
	fmt.Println("Add result:", result)

	container := Container[string]{
		Value: "hello",
		Items: []string{"world"},
	}
	container.Add("!")
	fmt.Println("Container:", container)

	cache := NewCache[string, int]()
	cache.Set("key1", 42)
	value, exists := cache.Get("key1")
	fmt.Printf("Cache get: %d, exists: %t\n", value, exists)
}