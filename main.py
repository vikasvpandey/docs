
from fastapi import FastAPI
from appconfig import AppConfig
from azureai import AzureAI
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import MessageLikeRepresentation
from langchain_core.runnables import RunnablePassthrough, Runnable
from typing import Sequence, Union
from operator import itemgetter


import json

app = FastAPI()

env = AppConfig()
azure = AzureAI(env)

async def create_runnable(prompt, model):
    print("Creating runnable for prompt.")
    # Add exception handling
    try:
        client = model or AzureAI(env).get_client()
        result = prompt | client | StrOutputParser()
    except Exception as e:
        logging.error(f"Error during runnable creation in main app: {e}")
        raise
    return result

# Refactor to accept an optional model and fallback to a default to improve flexibility
from langchain.schema import BaseMessage, HumanMessage, SystemMessage

async def convert_to_message_history(memory_list: list[str]):
    """Convert memory list to a message history sequence compatible with Langchain."""
    memory = []
    for i, message in enumerate(memory_list):
        if i % 2 == 0:
            memory.append(SystemMessage(content=message))
        else:
            memory.append(HumanMessage(content=message))
    return memory



#This returns a list of questions... ideally
@app.post('/get_questions')
async def get_questions(query_str: str):
    prompt = ChatPromptTemplate.from_messages([
        (
            "system",
            env.CHAT_PROMPT_TEMPLATE +
            r"Ensure the JSON response is as below: [{{\"question\": \"<question>\"}}]"
        ),
        ("human", "{query_str}")  # Pass query_str to the template
    ])
    
    model = azure.get_client()
    
    chain = await create_runnable(prompt, model)
    
    result = chain.invoke({"query_str": query_str})
    
    return {"questions": result}


@app.post('/get_usecase')
async def get_usecase(input_data: Union[dict[str, str], str]):
    print("Sending data to LLM for business case creation.")
    prompt = ChatPromptTemplate.from_messages([
        ("system",
                """
                🎯 Objective
                        Develop a comprehensive business case by combining strategic analysis, financial modeling, and ROI evaluation with detailed cost and revenue projections.

                        1. 💡 Concept Overview
                            Value Proposition: Define the unique problem solved.
                            Innovation: Highlight the distinctive solution.
                            Market Positioning: Explain competitive differentiation.
                        2. 📝 Detailed Description
                            Problem Statement: Current challenges and solution gaps.
                            Solution: Functional details and unique approach.
                            Target Market: Primary and secondary customer segments.
                        3. 🔧 Solution Architecture
                            Technology Stack: Core technologies and integrations.
                            Components: Key modules and scalability strategies.
                        4. 🚀 Benefits Analysis
                            Operational Gains: Efficiency and cost improvements.
                            Financial Impact: Revenue and savings potential.
                            Performance Benchmarks: Compare with existing solutions.
                        5. 🛠 Prerequisites
                            Technical: Infrastructure and readiness.
                            Organizational: Skills and resources.
                            External: Regulatory and ecosystem factors.
                        6. ⚠️ Risks
                            Comprehensive risk identification and mitigation.
                        7. 📊 Success Metrics
                            KPIs: Define, measure, and compare performance.
                        8. 👥 Resource Plan
                            Team: Roles and responsibilities.
                            Allocation: Resource distribution by phase.
                        9. 📝 Assumptions
                            Map and validate critical assumptions.
                        10. 🔗 Dependencies
                            Internal and external interdependencies, potential constraints.
                        11. 🧠 Skills Matrix
                            Required skills and proficiency levels.



                        12. 💰 Comprehensive ROI Analysis:
                            Generate a detailed ROI report in a tabular format with the following columns: Category, Component, Cost/Revenue, Calculations, and Assumptions. 
                            Use market-standard rates and realistic benchmarks for all calculations. Avoid using example values provided earlier; instead, rely on industry averages 
                            and typical ranges for costs. In the "Assumptions" column, provide meaningful assumptions based on market research or industry trends. 
                            Ensure deployment costs are specific to software products, including app store fees, SaaS hosting, or platform integrationsThe main section to cover are:
                               - **Development Costs:**
                                    Definition: Costs associated with building the product or solution.
                                    
                                    use following components as an example:
                                        - **Labor Costs:** Team salaries based on effort hours.
                                                Use a standard hourly rate for developers based on industry averages(e.g $20/hr to $80/hr).
                                                Labor Cost=(Hourly Rate)×(Number of Developers)×(Effort Hours)
                                            
                                        - **Software Tools/Subscriptions:** Licensing fees for tools (e.g., IDEs, libraries).
                                                Use typical licensing costs for industry-standard tools (e.g., IDEs, libraries).
                                                Tool Cost=(Tool License Cost/month)×(Number of Licenses) * (Time/month)
                                            Example:
                                                Tool Cost = $100/month * 10 licenses * 6 months
                                                Tool Cost = $6,000
        
                                - **Testing Costs:**
                                    Definition: Costs for quality assurance, testing tools, and beta user testing.
                                    use following components as an example:
                                        - **QA Team Labor Costs:**
                                                Use average QA engineer hourly rates
                                                QA Labor Cost=(Hourly Rate)×(Number of QA Engineers)×(Effort Hours)
                                            Example:
                                                QA Labor Cost = $40/hr * 10 engineers * 80 Hours
                                                QA Labor Cost = $32,000
                                        - **Testing Tools and Platforms:** Automated testing tools.
                                                Assume typical subscription costs for automated testing tools.
                                                Testing Tool Cost=(Tool Subscription Cost)×(Months Used)
                                            Example:
                                                Testing Tool Cost = $500/month * 6 months
                                                Testing Tool Cost = $3,000
                                - **Deployment Costs:**
                                    Definition: Costs incurred while in production and launching the product in the market.
                                    use following components as an example:
                                    - **Infrastructure Setup:** Cloud servers, databases.
                                            Use standard cloud subscription rates (e.g., AWS, Azure, or GCP).
                                            Infrastructure Cost=(Cloud Subscription Rate/month)×(Months Used)
                                        Example:
                                            Infrastructure Cost = $1,000/month * 6 months 
                                            Infrastructure Cost = $6,000 
                                    - **Marketing and Promotions:**
                                            Assume average costs per marketing campaign.
                                            Marketing Cost=(Cost per Campaign)×(Number of Campaigns)
                                        Example:
                                            Marketing Cost = $10,000/compaign * 5 campaigens
                                            Marketing Cost = $50,000
                                - **Operational Costs:**
                                    Definition: Recurring monthly costs after deployment.
                                    use following components as an example:
                                        - **Salaries:**
                                                Use market averages for employee salaries.
                                                Monthly Salary Cost=(Monthly Salary per Employee)×(Number of Employees)
                                            Example:
                                                Monthly Salary Cost = $5,000/employee * 20 employees 
                                                Monthly Salary Cost = $100,000/month
                                - **Total Cost:**
                                    Component
                                    - **total cost:**
                                        sum of Development Costs, Testing Costs, Deployment Costs and Operational Costs.

                                - **Revenue Projections:**
                                    Revenue estimation is based on market size, pricing, and customer acquisition.
                                    use following components as an example:

                                        - **Revenue Formula:**
                                                Use typical customer acquisition numbers and revenue per customer for similar industries.
                                                Revenue=(Number of Customers Acquired)×(Revenue per Customer)
                                            Example:
                                                Revenue = 1,000 customers * $500/customer
                                                Revenue = $500,000/year
                                        - **Customer Acquisition:** Use market research to estimate the number of customers over a timeframe.
                                        - **Pricing Model:** Define pricing per user or per transaction.
                                                Example:
                                                Expected 1,000 customers in year 1, each generating $500 in revenue annually:
                                                Revenue Year 1=1,000×500=$500,000
                                - **Breakeven Analysis:**
                                    - Calculate the breakeven point, indicating when the startup is expected to cover all costs.
                                    - Use the following formula to calculate the breakeven point:
                                            Breakeven Point(Months) = Total Costs/monthly revenue
                                
                                - **Net Profit:**
                                - component
                                    - **Net Earning:** 
                                        Calculate the net earning by subtracting total costs from total revenue.
                                        Net Profit = Total Revenue - Total Cost

                                - **ROI Calculation**
                                        Return on Investment (ROI) measures financial returns relative to the total costs.
                                        Use the following formula to calculate the ROI:
                                            ROI(%) = (Net Profit/Total Cost)*100
                                        - for example:
                                            - Total Revenue: $1,000,000
                                            - Total Cost: $500,000
                                            - ROI: (500,000/500,000)*100 = 100%

                                
                                Make it in the Tabuler form with Column names
                                Category
                                Component 
                                Cost 
                                Calculations
                                Assumptions
        """),
        ("human", "{input}")
    ])
    runnable = await create_runnable(prompt, "input")
    response = runnable.invoke({"input": json.dumps(input_data)})
    return response


@app.post('/refine_usecase')
async def refine_usecase(
    request: str,  # Expect a dictionary with a 'request' key
    memory_list: list[str]
):
    # Validate input structure
    
    # Convert memory list to message history format
    memory_variables = await convert_to_message_history(memory_list)

    # Define the prompt
    prompt = ChatPromptTemplate.from_messages([
        ("system", "You are a helpful assistant who helps users refine their business case based on the request and the provided business case in the history. Your response should be the refined business case unless the user is looking for something else."),
        MessagesPlaceholder(variable_name="history"),  # Placeholder for history
        ("human", "{request}")
    ])

    # Get the LLM client
    llm = azure.get_client()

    # Create the runnable chain
    runnable = (
        RunnablePassthrough.assign(
            history=memory_variables  # Pass memory_variables as 'history'
        )
        | prompt                      # Use the prompt with the 'history' placeholder
        | llm                         # Pass through to the LLM client
        | StrOutputParser()           # Parse the output from the LLM
    )

    # Execute the runnable chain and collect response
    response = ""
    async for chunk in runnable.astream({"request": request}):  # Pass the 'request' input
        response += chunk

    # Append the response to memory_list
    memory_list.append(response)

    # Return the response and updated memory
    return {"refined_usecase": response, "message_history": memory_list}

    
