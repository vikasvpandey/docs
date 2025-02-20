// ... existing code ...

def ask_question(question):
    try:
        # Modified code to handle JSON issues
        response = json.loads(question)
        return response['answer']
    except json.JSONDecodeError:
        print('Error: Unable to decode the question as JSON.')
        return None
    # Handle possible missing 'answer' key more gracefully
    except KeyError:
        print('Error: No answer found in the question data.')
        return None

// ... existing code ...