function hello() {
    console.log("Hello World");
}

function add(a, b) {
    return a + b;
}

class Calculator {
    multiply(x, y) {
        return x * y;
    }
    
    divide(x, y) {
        return x / y;
    }
}

// Run
hello();
console.log(`Add: ${add(5, 3)}`);

const calc = new Calculator();
console.log(`Multiply: ${calc.multiply(4, 7)}`);
console.log(`Divide: ${calc.divide(10, 2)}`);
