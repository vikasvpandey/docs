#this is a test py file
def sum_num(num1, num2=None):
    """
    Sum numbers with handling for missing parameters.
    """
    if num1 is None or num2 is None:
        raise ValueError("Both num1 and num2 must be provided.")
    return num1 + num2

# Test case with both arguments provided
result = sum_num(10, 20)
print(result)
result=sum_num(10)
print(result)
