# main.py

def multiply(a, b):
    """This function returns the product of a and b."""
    try:
        result = a * b
        return result
    except TypeError:
        raise ValueError("Both a and b must be numbers")


def main():
    print("Multiplication Program")
    num1 = 10
    num2 = 5
    print(f"The product of {num1} and {num2} is {multiply(num1, num2)}")


if __name__ == "__main__":
    main()