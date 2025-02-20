def calculate_sum(numbers):
    total = 0
    for number in numbers:
        total += number
    return total

# Example usage
if __name__ == '__main__':
    numbers_list = [1, 2, 3, 4, 5]
    print(f'The sum is: {calculate_sum(numbers_list)}')