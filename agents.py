
from autogen_agentchat.ui import Console
from autogen_agentchat.teams import RoundRobinGroupChat
from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.conditions import TextMentionTermination, MaxMessageTermination
from autogen_ext.models.openai import OpenAIChatCompletionClient
from autogen_agentchat.messages import TextMessage
from autogen_core.tools import FunctionTool
from appconfig import AppConfig
from azureai import AzureAI
from pydantic import BaseModel

from autogen_ext.tools.langchain import LangChainToolAdapter
from langchain_community.utilities import GoogleSerperAPIWrapper
from langchain.tools import Tool
import asyncio




    
def get_model():
    print('Initializing Azure AI model...')
    try:
        model_client = AzureAI(AppConfig()).get_client_autogen()
        print('Model successfully initialized.')
        return model_client
    except Exception as e:
        print(f'Failed to initialize model: {e}')
        raise
model = get_model()


# Define functions for CostCalculator methods
def compute_cost(effort_hours: float, manpower: int, hourly_rate: float = 50, contingency: float = 0.2) -> float:
    base_cost = effort_hours * manpower * hourly_rate
    total_cost = base_cost * (1 + contingency)
    
    return total_cost

def calculate_monthly_benefits(
    user_count: int = 100,  # Default to 100 users
    efficiency_gain: float = 0.3,  # 30% efficiency gain (common for digital transformation)
    hourly_rate: float = 50,       # $50 per hour (industry avg for knowledge workers)
    industry_multiplier: float = 0.2  # 1.2x (adjustment for indirect benefits in tech sector)
) -> float:
    """
    Estimates monthly benefits based on user count and efficiency gains using industry benchmarks.

    Default values:
    - User Count: 100 → Assumes medium-scale adoption in an organization
    - Efficiency Gain: 30% (0.3) → Common range: 25-35% for digital transformation
    - Hourly Rate: $50/hr → Based on IT/Software industry salaries
    - Industry Multiplier: 1.2 → Accounts for indirect benefits like collaboration and process improvements
    """
    monthly_benefits = user_count * efficiency_gain * hourly_rate * industry_multiplier * 160  # 160 avg monthly working hours
    return monthly_benefits

def calculate_annual_benefits(
    num_employees: int = 20,
    annual_cost_per_employee: float = 30000,
    efficiency_improvement: float = 0.10,  # 10% improvement
    agents_reduced: int = 2,
    annual_cost_per_agent: float = 15000
) -> dict:
    """
    Calculates annual benefits from operational efficiency improvements and support cost savings.
    
    Args:
        num_employees: Number of employees affected by efficiency improvements
        annual_cost_per_employee: Annual cost per employee
        efficiency_improvement: Percentage improvement in efficiency (0-1)
        agents_reduced: Number of support agents reduced
        annual_cost_per_agent: Annual cost per support agent
    
    Returns:
        Dictionary containing support savings, operational savings, and total annual benefits
    """
    # Calculate support cost savings
    support_savings = agents_reduced * annual_cost_per_agent
    
    # Calculate operational efficiency savings
    savings_per_employee = annual_cost_per_employee * efficiency_improvement
    operational_savings = num_employees * savings_per_employee
    
    # Calculate total annual benefits
    total_benefits = support_savings + operational_savings
    print("support_savings :", support_savings)
    print("operational_savings :", operational_savings)

    return total_benefits

def calculate_roi(total_cost: float, total_benefits: float) -> float:
    #annual_benefits = monthly_benefits*12
    if total_cost == 0:
        return 0
    return ((total_benefits - total_cost) / total_cost) * 100

def calculate_payback_period(total_cost: float, total_benefits: float) -> float:
    monthly_benefits = total_benefits / 12
    if total_benefits <= 0:
        return float('inf')
    return total_cost / monthly_benefits

# Wrap the functions in FunctionTool
cost_calculator_tool = FunctionTool(
    compute_cost,
    description="Calculates the total cost based on effort hours, manpower, hourly rate, and contingency."
)

monthly_benefits_tool = FunctionTool(
    calculate_monthly_benefits,
    description="Estimates monthly financial benefits based on user count, efficiency gains, and industry multipliers."
)

roi_tool = FunctionTool(
    calculate_roi,
    description="Calculates the ROI based on total cost and annual benefits."
)

payback_period_tool = FunctionTool(
    calculate_payback_period,
    description="Calculates the payback period based on total cost and monthly benefits."
)

annual_benefits_tool = FunctionTool(
    calculate_annual_benefits,
    description="Estimates annual benefit based on user count, efficiency gains, and industry multipliers."
)

class ComplexityParams(BaseModel):
    integration_count: int = 0
    ui_screens: int = 0
    data_migration_required: bool = False
    custom_development_needed: bool = False
    regulatory_compliance: bool = False

def assess_complexity(params: ComplexityParams) -> dict:
    """
    Assesses project complexity based on various parameters
    """
    score = 0
    factors = []
    
    # Integration complexity
    if params.integration_count > 0:
        score += params.integration_count * 2
        factors.append(f"Requires {params.integration_count} system integrations")
    
    # UI complexity
    if params.ui_screens > 0:
        score += params.ui_screens
        factors.append(f"Includes {params.ui_screens} UI screens")
    
    # Other factors
    if params.data_migration_required:
        score += 3
        factors.append("Data migration required")
    if params.custom_development_needed:
        score += 4
        factors.append("Custom development needed")
    if params.regulatory_compliance:
        score += 3
        factors.append("Regulatory compliance requirements")
    
    # Determine complexity level
    complexity_level = "Low" if score <= 5 else "Medium" if score <= 10 else "High"
    
    return {
        "complexity_level": complexity_level,
        "complexity_score": score,
        "contributing_factors": factors
    }

complexity_assessment_tool = FunctionTool(
    assess_complexity,
    description="Assesses project complexity based on integration count, UI screens, and other factors"
)

class StoryPoint(BaseModel):
    points: int = 1  # 1, 2, 3, 5, 8, 13
    complexity: str = "low"  # low, medium, high

def convert_story_points_to_hours(story_point: StoryPoint) -> float:
    """Converts story points to hours based on complexity"""
    base_hours = {
        1: 4, 2: 8, 3: 12, 5: 20, 8: 32, 13: 52
    }
    complexity_multiplier = {
        "low": 1.0,
        "medium": 1.5,
        "high": 2.0
    }
    return base_hours.get(story_point.points, 4) * complexity_multiplier.get(story_point.complexity, 1.0)

story_points_tool = FunctionTool(
    convert_story_points_to_hours,
    description="Converts story points to hours considering complexity"
)

effort_breakdown_agent = AssistantAgent(
    name="Effort_Breakdown_Agent",
    system_message='''You are an expert project manager with extensive experience in enterprise software implementations.
    Follow these specific steps for effort breakdown and estimation:

    1. Initial Analysis:
       - Analyze the user's project idea
       - Identify organization context (size, industry, implementation type)

    2. Integration Assessment:
       - Identify required system integrations
       - Document each integration's purpose and complexity

    3. Component Definition:
       - Break down into components (UI, Database, APIs, etc.)
       - Identify UI screens and forms needed
       - Determine data migration requirements
       - Check for custom development needs
       - Verify regulatory compliance requirements

    4. Complexity Assessment:
       - Use complexity_assessment_tool with gathered information
       - Consider integration count, UI screens, data migration, etc.
       - Document complexity factors and scores

    5. User Story Breakdown:
       - Break each component into user stories
       - Assign story points (1,2,3,5,8,13)
       - Use story_points_tool to convert to hours
       - Apply complexity-based weights

    6. Cost Calculation:
       - Use cost_calculator_tool for each work package
       - Consider complexity adjustments
       - Include resource requirements

    Output Format (JSON):
    {
        "project_context": {
            "organization_size": "",
            "industry": "",
            "implementation_type": ""
        },
        "implementation_details": {
            "integration_count": X,
            "ui_screens": X,
            "data_migration_required": true/false,
            "custom_development_needed": true/false,
            "regulatory_compliance": true/false
        },
        "complexity_assessment": {
            // Output from complexity_assessment_tool
        },
        "components": [
            {
                "name": "",
                "type": "UI/Database/Integration/etc",
                "stories": [
                    {
                        "description": "",
                        "story_points": X,
                        "complexity": "low/medium/high",
                        "estimated_hours": X,
                        "resources_required": X
                    }
                ]
            }
        ],
        "work_packages": [
            {
                "name": "",
                "description": "",
                "complexity": "low/medium/high",
                "estimation": {
                    "effort_hours": X,
                    "resources_count": X,
                    "cost": X
                },
                "technical_dependencies": [],
                "risks": [],
                "assumptions": []
            }
        ],
        "metadata": {
            "total_effort_hours": X,
            "total_cost": X,
            "estimated_duration_weeks": X,
            "key_risks": [],
            "critical_success_factors": []
        }
    }

    Guidelines:
    - Use industry benchmarks for similar projects
    - Consider complexity impacts on effort and cost
    - Document assumptions and risks clearly

    For effort estimation, create a detailed breakdown table with the following columns:
    Component | Type | Story Points | Complexity | Estimated Hours | Resources Required | Hourly Rate | Total Cost

    Calculate the cost for each component using the cost_calculator_tool:
    1. Use the estimated hours as effort_hours
    2. Use resources required as manpower
    3. Use standard hourly rates based on component type:
       - Integration: $75/hour
       - APIs: $70/hour
       - UI Design: $60/hour
       - Database: $65/hour
       - Regulatory/Compliance: $80/hour
       - Testing: $55/hour
    4. Apply complexity-based contingency:
       - High: 30% contingency
       - Medium: 20% contingency
       - Low: 10% contingency

    Example Table Format:
    {
        "components": [
            {
                "name": "WhatsApp API Integration",
                "type": "Integration",
                "story_points": 8,
                "complexity": "High",
                "estimated_hours": 320,
                "resources_required": 3,
                "hourly_rate": 75,
                "cost_calculation": {
                    "base_cost": 72000,  // (320 hours * 3 resources * $75)
                    "contingency": 21600, // (30% for high complexity)
                    "total_cost": 93600
                }
            }
        ],
        "total_estimation": {
            "total_hours": X,
            "total_resources": X,
            "total_cost": X
        }
    }

    For each component:
    1. Convert story points to hours using story_points_tool
    2. Apply complexity multiplier to hours
    3. Calculate cost using cost_calculator_tool
    4. Include all details in the component breakdown
    5. Sum up totals for the project
    ''',
    tools=[cost_calculator_tool, complexity_assessment_tool, story_points_tool],
    model_client=model
)
    
cost_and_savings_agent = AssistantAgent(
    name="cost_and_savings_agent",
    system_message='''Act as a financial analyst specializing in annual savings and initial cost calculation enterprise software solutions.
    Your primary task is to consume JSON data provided by the Effort_Breakdown_Agent and create a detailed effort estimation plan, and cost breakdown.
 
    Use the complexity_assessment from the input JSON to adjust your calculations:
    - For "High" complexity: Add 40% to base costs and reduce efficiency improvements by 20%
    - For "Medium" complexity: Add 20% to base costs and reduce efficiency improvements by 10%
    - For "Low" complexity: Use base calculations
    
    Key Outputs:
    - Comprehensive project overview with assumptions and high-level solution architecture.
    - Detailed effort estimation in tabular format.
    - Clear cost estimation including direct, indirect, licensing, and subscription costs.

    Format your output under clear headings and subheadings, including:
    - **Project Overview**
        - Include complexity level and score from complexity_assessment
        - List contributing complexity factors
    - **Assumptions**
    - **Effort Estimation** (in tabular form)
    - **Cost Estimation**:
        - **Direct Cost**: sum of all the stories cost, adjusted for complexity
        - **Indirect Cost**: take 30% of Direct cost if not given
        - **Complexity Adjustment**: Additional cost based on complexity level
        - **Total Cost**: sum of Direct Cost, Indirect Cost, and Complexity Adjustment
        
    - **Annual Savings**: Calculate and present annual savings based on efficiency improvements.
        - Must use **annual_benefits_tool** with the following parameters and adjust the default values according to usecase and complexity:
            num_employees: int = 20,
            annual_cost_per_employee: float = 70000,
            efficiency_improvement: float = (0.10 adjusted based on complexity),
            agents_reduced: int = 2,
            annual_cost_per_agent: float = 30000
    ''',
    tools=[annual_benefits_tool, complexity_assessment_tool],
    model_client=model
)

finance_analyst_agent = AssistantAgent(
    name="Finance_analyst_and_Roi_Agent",
    system_message='''Act as a financial analyst specializing in ROI for enterprise software solutions.
    Your primary task is to consume data provided by the cost_and_savings_agent and calculate ROI and Payback.
    
    Adjust your analysis based on the complexity_assessment from the original JSON:
    - For "High" complexity projects:
        - Add risk factors to ROI calculations
        - Extend expected payback period
        - Consider phased benefits realization
    - For "Medium" complexity projects:
        - Add moderate risk adjustments
        - Standard payback period calculations
    - For "Low" complexity projects:
        - Use standard calculations
        - Faster benefit realization timeline
 
    Key Outputs:
    - **Complexity-Adjusted Analysis**:
        - Summary of complexity level and its impact on financial projections
        - Risk factors based on complexity assessment
    
    - **ROI Analysis**:
        - Use **roi_tool** tool for ROI Analysis
        - for roi calculation total_benefits will come from cost_and_savings_agent
        - for roi calculation total_cost will come from effort_breakdown_agent & cost_and_savings_agent including all provided factors
        - Show ROI projections for years 1-5
        - Include complexity-based risk adjustments
    
    - **Payback Period**:
        - Use **payback_period_tool** tool
        - Adjust for complexity-based factors
        - Include best/worst case scenarios based on complexity
 
    Ensure to present expected benefits compared to total estimated costs, and identify potential risks with mitigation strategies.
    
    Remember: Your role is to provide realistic, complexity-adjusted financial projections.
 
    MENTION TERMINATE IF TASK IS DONE
    ''',
    tools=[roi_tool, payback_period_tool, complexity_assessment_tool],
    model_client=model
)
    
termination = TextMentionTermination("TERMINATE")
group_chat = RoundRobinGroupChat([effort_breakdown_agent, cost_and_savings_agent, finance_analyst_agent], termination_condition= termination) 
print("group chat :", group_chat)

async def run_group_chat(query: str):
    try:
        messages = []
        stream = group_chat.run_stream(task=query)
       
        # Process all messages in the stream
        async for msg in stream:
            if isinstance(msg, TextMessage) and msg.source != "user":
               
                # Check for termination message
                if "TERMINATE" in msg.content:
                    print("\n=== Chat Terminated ===")
                    messages.append(msg.content)
                    print(msg.content)
        return messages
            
    except Exception as e:
        print(f"Error occurred: {str(e)}")
        import traceback
        print(traceback.format_exc())
        return []


if __name__ == "__main__":
    # Test query
    sample_query = "Our retail chain wants to migrate from an on-prem ERP system to a cloud-based SAP solution"
    asyncio.run(run_group_chat(sample_query))
