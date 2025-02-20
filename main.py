def multiply_numbers(a, b):
    # Ensure the inputs are numbers
    if not (isinstance(a, (int, float)) and isinstance(b, (int, float))):
        raise ValueError("Both inputs must be numbers")
    return a * b

# Example usage
result = multiply_numbers(5, 3)
print(f"The result of multiplication is: {result}")