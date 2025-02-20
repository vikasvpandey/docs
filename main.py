# main.py

def calculate_sum(numbers):
    """Calculate the sum of a list of numbers, ensuring all elements are numeric."""
    if not all(isinstance(n, (int, float)) for n in numbers):
        raise ValueError("All elements must be numbers")
    return sum(numbers)


def main():
    try:
        total = calculate_sum([1, 2, '3', 4])
        print(f"The sum is: {total}")
    except ValueError as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    main()
