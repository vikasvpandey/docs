def process_agent_response(response: str) -> str:
    """Helper function to process and validate agent responses"""
    if not response or response.isspace():
        raise Exception("Agent returned empty response")
    
    # Clean up the response
    response = response.strip()
    if response.startswith('```json'):
        response = response[7:].strip()
    if response.endswith('```'):
        response = response[:-3].strip()
    
    # Validate the response
    if 'Analyze this' in response:
        raise Exception("Agent returned the prompt instead of a response")

    # Additional validation to ensure response is JSON
    try:
        json_response = json.loads(response)
        if not isinstance(json_response, dict):
            raise Exception("Agent response is not a valid JSON object")
    except json.JSONDecodeError:
        raise Exception("Response is not valid JSON")
    
    return response