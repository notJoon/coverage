"""
Sample Python file to test our coverage instrumentation
"""


def factorial(n):
    """Calculate factorial of n"""
    if n <= 1:
        return 1
    else:
        return n * factorial(n - 1)


def fibonacci(n):
    """Calculate the nth Fibonacci number"""
    if n <= 0:
        return 0
    elif n == 1:
        return 1
    else:
        return fibonacci(n - 1) + fibonacci(n - 2)


def is_prime(n):
    """Check if a number is prime"""
    if n <= 1:
        return False
    if n <= 3:
        return True
    if n % 2 == 0 or n % 3 == 0:
        return False
    i = 5
    while i * i <= n:
        if n % i == 0 or n % (i + 2) == 0:
            return False
        i += 6
    return True


# Main execution
if __name__ == "__main__":
    print("Calculating factorial of 5:", factorial(5))
    print("Calculating 7th Fibonacci number:", fibonacci(7))

    print("Is 1, 2, 3 prime?")
    for i in range(1, 4):
        print(f"{i} is prime: {is_prime(i)}")
    print("Is 17 prime?", is_prime(17))

    # Conditional branch (only one side executed)
    x = 10
    if x > 5:
        print("x is greater than 5")
    else:
        print("x is not greater than 5")
