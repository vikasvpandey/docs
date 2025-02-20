import json

def calculate_sum(file_path):
    try:
        with open(file_path, 'r') as file:
            data = json.load(file)
            
            # Assume the JSON file is a list of numbers
            if isinstance(data, list) and all(isinstance(i, (int, float)) for i in data):
                total_sum = sum(data)
                return total_sum
            else:
                raise ValueError('JSON data is not a list of numbers')
    except FileNotFoundError:
        print(f"File not found: {file_path}")
    except json.JSONDecodeError:
        print("Error decoding JSON from the file.")
    except Exception as e:
        print(f"An error occurred: {str(e)}")

# Example usage
if __name__ == "__main__":
    sum_result = calculate_sum('test.json')
    print(f'Sum of numbers: {sum_result}')