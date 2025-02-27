import os
from github import Github
import logging
from typing import Dict, List
import asyncio
from config.appconfig import AppConfig
from config.azureai import AzureAI
from autogen_agentchat.agents import AssistantAgent
from src.infrastructure_executor import InfrastructureExecutor
from src.env_issue_handler import EnvironmentIssueHandler
from src.code_issue_handler import CodeIssueHandler
import json

# Initialize configurations
env = AppConfig()
GITHUB_TOKEN = os.getenv('GITHUB_TOKEN')
GITHUB_REPO = 'vikasvpandey/docs'

def get_ai_client():
    return AzureAI(AppConfig()).get_client()

def create_system_prompt(docs: list) -> str:
    return f"""
    You are a knowledgeable assistant designed to help users by solving code in repository.

    **Instructions:**
    1. Use these documents for reference: {docs}
    2. For your response:
        - check the code repo, and fix the code as per issue given in reference docs
    """

def create_issue_classifier_agent():
    """Creates an agent that classifies issues as code-related or environment-related"""
    system_prompt = """
    You are an expert issue classifier who determines if an issue requires code fixes or environment/DevOps fixes.
    
    When analyzing an issue:
    1. Look for keywords and patterns indicating:
       - Code issues: bugs, syntax errors, logic errors, performance issues, memory leaks
       - Environment issues: deployment failures, scaling issues, configuration problems, resource constraints, 
         connectivity issues, permission issues, infrastructure problems
    
    2. Respond with a JSON object only:
    {
        "issue_type": "code" or "environment",
        "confidence": float between 0-1,
        "reasoning": "brief explanation",
        "suggested_approach": "specific suggestion for resolution"
    }
    
    3. Be decisive - always classify as either "code" or "environment"
    """
    
    return AssistantAgent(
        name="issue_classifier",
        model_client=get_ai_client(),
        system_message=system_prompt
    )

class AutoRemediation:
    def __init__(self):
        self.github = Github(GITHUB_TOKEN)
        self.repo = self.github.get_repo(GITHUB_REPO)
        self.env_handler = EnvironmentIssueHandler(self.github, self.repo)
        self.code_handler = CodeIssueHandler(self.github, self.repo)
        
    async def create_github_issue(self, ticket_data: Dict) -> Dict:
        """Create a GitHub issue from ServiceNow ticket data"""
        try:
            # Extract ticket information
            title = ticket_data.get('short_description', 'No title provided')
            description = ticket_data.get('description', 'No description provided')
            urgency = ticket_data.get('urgency', '3')
            
            # Create labels based on urgency
            labels = ['auto-remediation']
            if urgency == '1':
                labels.append('high-priority')
            elif urgency == '2':
                labels.append('medium-priority')
            
            # Create the GitHub issue
            issue = self.repo.create_issue(
                title=f"[Auto-Remediation] {title}",
                body=f"""
                **ServiceNow Ticket Details**
                
                {description}
                
                **Priority Level**: {urgency}
                
                This issue was automatically created from a ServiceNow ticket.
                """,
                labels=labels
            )
            print(f"Created GitHub issue: {issue.number}")
            return {
                "success": True,
                "issue_number": issue.number,
                "issue_url": issue.html_url
            }
            
        except Exception as e:
            print(f"Error creating GitHub issue: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }

    async def analyze_and_fix_issue(self, issue_number: int) -> Dict:
        """Delegate to code issue handler"""
        return await self.code_handler.analyze_and_fix_issue(issue_number)

    async def analyze_and_fix_env_issue(self, issue_number: int) -> Dict:
        """Delegate to environment issue handler"""
        return await self.env_handler.analyze_and_fix_env_issue(issue_number)

async def handle_servicenow_ticket(ticket_data: Dict) -> Dict:
    """Main handler for processing ServiceNow tickets and initiating auto-remediation"""
    try:
        auto_remediate = AutoRemediation()
        
        # Create GitHub issue
        github_issue = await auto_remediate.create_github_issue(ticket_data)
        
        if not github_issue['success']:
            return {
                "success": False,
                "message": f"Failed to create GitHub issue: {github_issue.get('error')}"
            }
        
        # Create classifier agent
        classifier_agent = create_issue_classifier_agent()
        
        # Get classification
        classification_prompt = f"""Analyze this issue and classify it as code or environment related:
Title: {ticket_data.get('short_description')}
Description: {ticket_data.get('description')}"""
        
        logging.info(f"Classification prompt: {classification_prompt}")
        
        # Get classification from agent
        classification_result = await get_classification(classifier_agent, classification_prompt)
        
        # Choose appropriate fix method based on classification
        if classification_result['issue_type'] == 'code':
            logging.info("Processing as code issue")
            remediation_result = await auto_remediate.analyze_and_fix_issue(
                github_issue['issue_number']
            )
        else:  # environment issue
            logging.info("Processing as environment issue")
            remediation_result = await auto_remediate.analyze_and_fix_env_issue(
                github_issue['issue_number']
            )
        
        return {
            "success": True,
            "github_issue": github_issue,
            "classification": classification_result,
            "remediation_result": remediation_result
        }
        
    except Exception as e:
        logging.error(f"Error in auto-remediation process: {str(e)}")
        logging.error(f"Full error context: {str(e.__class__.__name__)}: {str(e)}")
        return {
            "success": False,
            "message": f"Auto-remediation failed: {str(e)}"
        }

async def get_classification(agent: AssistantAgent, prompt: str) -> Dict:
    """Helper function to get classification from agent"""
    classification_response = ""
    last_response = ""
    
    try:
        async for chunk in agent.run_stream(task=prompt):
            if hasattr(chunk, 'messages'):
                for message in chunk.messages:
                    if message.source == 'assistant':
                        last_response = message.content
            elif hasattr(chunk, 'content'):
                last_response = chunk.content
            elif isinstance(chunk, str):
                classification_response += chunk
        
        # Use the last response if available, otherwise use accumulated response
        response = last_response if last_response else classification_response
        
        # Process and validate the response
        response = process_agent_response(response)
        classification_data = json.loads(response)
        
        # Add additional logging for debugging purposes
        logging.info(f'Classification result: {classification_data}')
        
        return classification_data
        
    except Exception as e:
        logging.error(f"Error in classification: {str(e)}")
        raise
def process_agent_response(response: str) -> str:
    """Helper function to process and validate agent responses"""
    if not response or response.isspace():
        raise Exception("Agent returned empty response")
    
    # Clean up the response
    response = response.strip()
    if response.startswith('```json'):
        response = response[7:]
    if response.endswith('```'):
        response = response[:-3]
    response = response.strip()
    
    # Validate the response
    if response.startswith("Analyze this"):
        raise Exception("Agent returned the prompt instead of a response")
    
    return response

if __name__ == "__main__":
    asyncio.run(handle_servicenow_ticket({"short_description": "I am not getting questions prompts"}))
