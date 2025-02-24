// ... existing code ...
def ask_question():
    try:
        # Read user input
        user_input = input("Please enter your question: ")
        
        # Validate user input
        if not user_input.strip():
            raise ValueError("Input cannot be empty.")
        
        # Process the valid input
        response = process_input(user_input)
        
        return response
    except ValueError as e:
        print(f"Error: {str(e)}")
        return "Please enter a valid question."
    except Exception as e:
        print(f"Unexpected error: {str(e)}")
        return "An unexpected error occurred. Please try again."

def process_input(user_input):
    # ... existing code that processes input ...
    return "Processed: " + user_input
// ... existing code ...