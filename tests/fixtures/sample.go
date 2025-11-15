package main

import (
	"encoding/json"
	"fmt"
	"net/http"
)

func simpleFunc(x int, y int) int {
	return x + y
}

func complexFunc(data []string) error {
	if len(data) == 0 {
		return fmt.Errorf("empty data")
	}
	for _, item := range data {
		switch item {
		case "a":
			fmt.Println("a")
		case "b":
			fmt.Println("b")
		default:
			fmt.Println("default")
		}
	}
	return nil
}

type User struct {
	Name string
	Age  int
}

type Handler interface {
	ServeHTTP(w http.ResponseWriter, r *http.Request)
}
