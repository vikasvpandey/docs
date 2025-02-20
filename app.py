

import json

def ask_question(data):
    try:
        # Assuming 'data' needs to be parsed as JSON
        question_data = json.loads(data)
        # Process the question as required
        question = question_data.get('question')
        # Simulate some processing of the question
        response = process_question(question)
        # Return a json string response
        return json.dumps({'status': 'success', 'response': response})
    except json.JSONDecodeError:
        return json.dumps({'status': 'error', 'message': 'Invalid JSON format'})
    except Exception as e:
        return json.dumps({'status': 'error', 'message': str(e)})


def process_question(question):
    # Placeholder function to simulate question processing
    if question:
        return f"Processed question: {question}"
    else:
        return "No question provided"
