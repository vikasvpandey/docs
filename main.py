// ... existing code ...

def ask_question(question):
    try:
        if not isinstance(question, str):
            raise ValueError("Question must be a string")

        # ... code that asks a question ...
        # Simulate getting an answer
        answer = "42"  # Dummy response for debugging

        print(f"Question: {question}")
        print(f"Answer: {answer}")
        return answer
    except Exception as e:
        print(f"An error occurred: {e}")
        return None

# ... existing code ...