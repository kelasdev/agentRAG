package main

import "fmt"

func Hello() {
	fmt.Println("Hello World")
}

func Add(a, b int) int {
	return a + b
}

type Calculator struct{}

func (c *Calculator) Multiply(x, y int) int {
	return x * y
}

func (c *Calculator) Divide(x, y int) int {
	return x / y
}

func main() {
	Hello()
	fmt.Printf("Add: %d\n", Add(5, 3))
	
	calc := &Calculator{}
	fmt.Printf("Multiply: %d\n", calc.Multiply(4, 7))
	fmt.Printf("Divide: %d\n", calc.Divide(10, 2))
}
