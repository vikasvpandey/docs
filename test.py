import json

# Function to handle JSON data safely
def safe_json_load(data):
    try:
        return json.loads(data)
    except json.JSONDecodeError as e:
        print(f'Error decoding JSON: {e}')
        return None

# Example usage
json_data = '{"key": "value"}'  # sample JSON string
result = safe_json_load(json_data)
if result is not None:
    print('JSON successfully parsed:', result)
else:
    print('Failed to parse JSON data.')