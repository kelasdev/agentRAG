def hello():
    print("Hello World")

def add(a, b):
    return a + b

class Calculator:
    def multiply(self, x, y):
        return x * y
    
    def divide(self, x, y):
        return x / y

if __name__ == "__main__":
    hello()
    print(f"Add: {add(5, 3)}")
    
    calc = Calculator()
    print(f"Multiply: {calc.multiply(4, 7)}")
    print(f"Divide: {calc.divide(10, 2)}")
