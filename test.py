def calculate_sum(numbers):
    if not all(isinstance(n, (int, float)) for n in numbers):
        raise ValueError('All elements must be numbers')
    return sum(numbers)

# Example code correction
numbers = [1, 2, 3, 4, 5]
result = calculate_sum(numbers)
print('The sum is:', result)