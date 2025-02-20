// ... existing code ...

def ask_question(input_json):
    try:
        # Parse the input json
        input_data = json.loads(input_json)
    except json.JSONDecodeError as e:
        # Handle the JSON decoding error
        print(f"Error decoding JSON: {e}")
        return None
    
    # Continue with processing the input_data
    # ... existing code ...

// ... existing code ...