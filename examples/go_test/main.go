package main

import "fmt"

type Greeter interface {
    Greet()
}

type Person struct {
    Name string
}

func (p Person) Greet() {
    fmt.Printf("Hello, %s!\n", p.Name)
}

func NewPerson(name string) Person {
    return Person{Name: name}
}

func main() {
    p := NewPerson("world")
    p.Greet()
}
