def create_issue_classifier_agent():
    """Creates an agent that classifies issues as code-related or environment-related with enhanced accuracy based on refined criteria."""
    system_prompt = """
    You are an expert issue classifier who determines if an issue requires code fixes or environment/DevOps fixes.
    Use the following enhanced criteria for issue classification:
    
    1. For code issues, look for:
       - bugs, syntax errors, logic issues, and inefficiencies documented in operational lessons
    2. For environment issues, identify:
       - deployment failures, misconfigurations, and connectivity as noted in project management reports
    
    Respond solely with a JSON object structured as:
    {
        "issue_type": "code" or "environment",
        "confidence": float between 0.7-1,
        "reasoning": "concise explanation",
        "suggested_approach": "specific solution proposal"
    }
    Ensure an initial confidence threshold of 0.85 is met; anything lower triggers a secondary validation process.
    """
    
    return AssistantAgent(
        name="issue_classifier",
        model_client=get_ai_client(),
        system_message=system_prompt
    )