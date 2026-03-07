public class Example {
    
    public static void hello() {
        System.out.println("Hello World");
    }
    
    public static int add(int a, int b) {
        return a + b;
    }
    
    static class Calculator {
        public int multiply(int x, int y) {
            return x * y;
        }
        
        public int divide(int x, int y) {
            return x / y;
        }
    }
    
    public static void main(String[] args) {
        hello();
        System.out.println("Add: " + add(5, 3));
        
        Calculator calc = new Calculator();
        System.out.println("Multiply: " + calc.multiply(4, 7));
        System.out.println("Divide: " + calc.divide(10, 2));
    }
}
