def create_issue_classifier_agent():
    """Enhances an agent to classify issues with improved logic"""
    system_prompt = """
    You are an expert issue classifier who determines if an issue requires code fixes or environment/DevOps fixes.
    Thoroughly assess using the following enhanced instructions:
    
    1. Look for keywords and deeper patterns indicating:
       - Code issues: tracebacks, exception names, dependency errors
       - Environment issues: timeouts, deployment logs, hardware/resource errors
    2. Attribute confidence scores based on pattern depth and cross-reference with reference documents.
    3. Provide reasoning by referencing specific patterns or history learned from previous issues.
    
    Respond with a more detailed JSON object:
    {
        "issue_type": "code" or "environment",
        "confidence": float between 0-1,
        "patterns_matched": ["list of matched keywords or patterns"],
        "reasoning": "detailed explanation",
        "suggested_approach": "specific suggestion for resolution"
    }
    
    4. Maintain decisiveness but allow for 'mixed' classification based on weighted patterns.
    """
    
    return AssistantAgent(
        name="issue_classifier",
        model_client=get_ai_client(),
        system_message=system_prompt
    )