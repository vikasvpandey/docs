import chainlit as cl
import logging
import chainlit as cl
import logging
from appconfig import AppConfig
from azureai import AzureAI
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.schema import StrOutputParser
from langchain.schema.runnable import RunnablePassthrough, RunnableLambda
from langchain.schema.runnable.config import RunnableConfig
from operator import itemgetter
from langchain.memory import ConversationBufferMemory
import json

import services

import re
import io
import base64
import pandas as pd


##for pydantic model validation
from typing import List, Optional, Union, cast
from langchain.output_parsers import PydanticOutputParser
from langchain_core.prompts import PromptTemplate
from langchain_core.pydantic_v1 import BaseModel, ValidationError, Field, validator


#ploting
import plotly.express as px
import plotly.graph_objects as go


from helper import save_case_generated


# Set log level to DEBUG for detailed logging
# logging.basicConfig(level=logging.DEBUG)

# Environment configuration
env = AppConfig()
# Initialize Azure AI model as a global variable
ai_model = AzureAI(env).get_client()
# print(f"ENV configuration loaded: {env.to_json()}")

questions = []
answers = []
user_idea = ""
item_id = None


async def initialize_memory():
    print("Initializing conversation memory.")
    cl.user_session.set("memory", ConversationBufferMemory(return_messages=True))
    # Reset global variables
    global answers, user_idea
    answers = []
    user_idea = ""


async def ask_action(content, options):
    print(f"Asking action: {content} with options: {options}")
    actions = [cl.Action(name=option, value=option, description=option.capitalize()) for option in options]
    response = await cl.AskActionMessage(content=content, actions=actions).send()

    if response:
        return response.get("name")
    else:
        return "No"

async def ask_user_message(content, timeout=20):
    print(f"Asking user message: {content} with timeout: {timeout}")
    memory = cl.user_session.get("memory")
    memory.chat_memory.add_ai_message(content)
    response = await cl.AskUserMessage(content=content, timeout=timeout).send()
    return response

async def ask_user_message_for_idea(content):
    return await ask_user_message(content)


async def send_message(content):
    print(f"Sending message: {content}")
    await cl.Message(content=content).send()

async def create_runnable(prompt, input_key):
    print("Creating runnable for prompt.")
    # Use global model instead of creating new instance
    return prompt | ai_model | StrOutputParser()

@cl.on_chat_start
async def on_chat_start():
    print("Chat started.")
    await initialize_memory()
    await send_message("Hello! I am your assistant to help you build a business case out of your idea.")
    response = await ask_action("Are you ready to submit your idea?", ["yes", "no"])
    if response == "yes":
        input = await ask_user_message_for_idea("Please share your idea.")
        print("Input idea", input)
        if not input or not input['output']:
            await send_message("Please start again when you are ready to submit your idea.")
        else:
            global user_idea
            user_idea = input['output']
            print(f"User idea received: {user_idea}")
            prompt = ChatPromptTemplate.from_messages([
                ("system", env.CHAT_PROMPT_TEMPLATE + " Ensure the JSON response is as below: [{{\"question\": <question>}}]"),
                ("human", "{input}")
            ])
            runnable = await create_runnable(prompt, "input")
            cl.user_session.set("runnable", runnable)
            await process_idea()
    else:
        await send_message("Please start again when you are ready to submit your idea.")

@cl.on_message
async def on_message(message: cl.Message):
    print(f"Message received: {message.content}")
    memory = cl.user_session.get("memory")

    remaining_questions = cl.user_session.get("remaining_questions")
    # Check if there are remaining questions to ask
    if remaining_questions is not None:
        await send_message("Welcome back! Let's continue where we left off, shall we?")       
        print(remaining_questions)
        await ask_remaining_questions(remaining_questions)

    prompt = ChatPromptTemplate.from_messages([
        ("system", "You are a helpful assistant who helps users to refine their business case based on the request and the provided business case in the history. Your response should be the refined business case unless the user is looking for something else."),
        MessagesPlaceholder(variable_name="history"),
        ("human", "{request}")
    ])
    runnable = (
        RunnablePassthrough.assign(
            history=RunnableLambda(memory.load_memory_variables) | itemgetter("history")
        )
        | prompt
        | ai_model
        | StrOutputParser()
    )
    user_input = message.content
    msg = cl.Message(content="")

    async for chunk in runnable.astream(
        {"request": user_input},
        config=RunnableConfig(callbacks=[cl.LangchainCallbackHandler()])
    ):
        await msg.stream_token(chunk)
    await msg.send()
    save_case = await ask_action("Would you like to save your report or refine them a bit further?", ["I would like to save", "Let me ask somethings a bit further"])
    if save_case == "I would like to save":
        global item_id
        item_id= await save_case_generated(user_idea, ans, item_id)
        send_message('Your Case has been saved') if item_id is not None else send_message('There has been an error saving your message, hold on...')

    print(f"User input processed: {user_input} && have I saved case? {save_case} with {item_id}")

    memory.chat_memory.add_user_message(message.content)
    memory.chat_memory.add_ai_message(msg.content)

async def process_idea():
    print("Processing user idea.")
    await send_message("Thank you for sharing your idea.")
    response = await ask_action("Are you ready to answer a few questions to understand the case?", ["yes", "no"])
    if response == "yes":
        runnable = cl.user_session.get("runnable")
        content = runnable.invoke({"input": user_idea})
        try:
            cleaned_content = content.strip().strip('```json').strip('```').strip()
            questions = json.loads(cleaned_content)
            print(f"Questions generated: {questions}")
            print("User is ready to answer questions.")
            await ask_question(0, questions)
        except json.JSONDecodeError as e:
            logging.error(f"Error decoding JSON: {e}")
            questions = []
    else:
        global ans
        ans = await create_business_case()
        save_case = await ask_action("Would you like to save your report or refine them a bit further?", ["I would like to save", "Let me ask somethings a bit further"])
        if save_case == "I would like to save":
            global item_id
            item_id = await save_case_generated(user_idea, ans, item_id)
            await send_message('Your Case has been saved') if item_id is not None else send_message('There has been an error saving your message, hold on...')


async def ask_question(index:int, questions: list):
    '''
    Getting response object for the question asked. 
    If the json and the key value output present, then it
    moves onto the on_answer function, else it goes to the cancel function
    '''
    if index < len(questions):
        print(f"Asking question {index}: {questions[index]['question']}")
        response = await ask_user_message(questions[index]["question"], timeout=120)
        if response and response["output"]:
            await on_answer(questions, index, response["output"])
        else:
            await on_cancel(questions, index)

async def on_answer(questions: list, index: int, answer: list):
    print(f"Received answer for question {index}: {answer}")
    memory = cl.user_session.get("memory")
    memory.chat_memory.add_user_message(answer) 
    question = questions[index]["question"]
    answers.append({"question": question, "answer": answer}) #we are creating an answer and then appending that
    index += 1
    if index < len(questions):
        await ask_question(index, questions)
    else:
        global ans
        ans = await create_business_case()
        save_case = await ask_action("Would you like to save your report or refine them a bit further?", ["I would like to save", "Let me ask somethings a bit further"])
        if save_case == "I would like to save":
            global item_id
            item_id = await save_case_generated(user_idea, ans, item_id)
            await send_message('Your Case has been saved') if item_id is not None else send_message('There has been an error saving your message, hold on...')


#index is being passed here. the questions start once again
async def on_cancel(questions: list, index: int):
    '''
    When cancelled prematurely or timed out, a new list array is created, and then set into memory
    '''
    print("Question answering timed out or was cancelled.")
    remaining_questions = questions[index:]
    cl.user_session.set("remaining_questions", remaining_questions)
    print("-------------------------------------------------------------- " 
          "-------------------------------------------------------------- ")
    print(remaining_questions)
    await send_message("Timed out - Action cancelled. You can resume the questions later.")

async def ask_remaining_questions(remaining_questions: list):
    print(f"Asking remaining questions: {remaining_questions}")
    for i, question in enumerate(remaining_questions):
        response = await ask_user_message(question["question"], timeout=20)    
        if response and response["output"]:
            await on_answer(remaining_questions, i, response["output"])  
        else:
            await on_cancel(remaining_questions, i)
            break
    cl.user_session.set("remaining_questions", [])

async def create_business_case():
    try:
        # First send the "Creating business case" message
        await send_message("Creating business case. Please wait")
        
        business_case = {
            "idea": user_idea,
            "Questions and Answers": answers
        }
        print(f"Creating business case: {business_case}")
        
        # Send LLM response as a regular message
        llm_response = await send_to_llm(business_case)
        await cl.Message(content=llm_response).send()
        print("LLM Response:", llm_response)

        # Create and send visualization separately
        dataframe = await parse_markdown_to_dataframe(llm_response)
        if not dataframe.empty:
            print("final dataframe:", dataframe)
            await plot_charts(df=dataframe, chart_type="bar")
            
    except Exception as err:
        print(f"An error occurred: {err}")



# We can go ahead and try to create an agent here for the visualization apart from the general template
async def send_to_llm(input_data):
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

    cl.user_session.set("business_case_response", response)


    memory = cl.user_session.get("memory")
    memory.chat_memory.add_ai_message(response)
    print("my Response:", response)
    return response
###################################################################################################

## ROI Visualization

# Remove duplicate env and model initialization
# env = AppConfig()
# model = AzureAI(env).get_client()


class RoiTableSchema(BaseModel):
    Category: str
    Component: str
    Cost: Union[int,float]
    Calculations: Optional[str] = ""
    Assumptions: Optional[str] = ""

        # Custom validator to clean numeric fields
    @validator("Cost", pre=True)
    def clean_numeric(cls, value):
        if isinstance(value, str):
            #remove $ and , characters
            cleaned_value = value.replace("$", "").replace(",", "").strip()
            
            # Handling percentages by removing % and converting to float
            if "%" in cleaned_value:
                return float(cleaned_value.replace("%", "").strip())
            try:
                ##convert the clean value to an int
                return int(cleaned_value)
            except ValueError:
                raise ValueError(f"Invalid cost value: {value}")
        return value

class RoiTableList(BaseModel):
    __root__: List[RoiTableSchema]


async def parse_markdown_to_dataframe(response: str):
    """
    Parses a markdown response into a DataFrame.

    Args:
        response (str): The markdown text to parse.

    Returns:
        pd.DataFrame: A DataFrame containing the parsed data.

    Raises:
        ValidationError: If the response fails validation.
        Exception: For any other processing errors.
    """
    # Define the PydanticOutputParser and PromptTemplate logic here
    parser = PydanticOutputParser(pydantic_object=RoiTableList)

    prompt = PromptTemplate(
        template=(
            "Extract the ROI Analysis table from the markdown input and return each row as JSON."
            "Ensure the keys match this structure: 'Category', 'Component', 'Cost', 'Calculations', 'Assumptions'."
            "Ensure numeric fields (Cost, Break_even_months) are integers without formatting (no $ or commas).\n"
            "{markdown_input}\n"
        ),
        input_variables=["markdown_input"],
    )

    # Use global ai_model instead of model
    chain = prompt | ai_model | parser

    try:
        # Process the markdown input through the chain
        result = await chain.ainvoke({"markdown_input": response})
        
        # Ensure the result is a list
        if isinstance(result, dict):
            result = [result]  # Wrap single dict in a list


        # Convert result to a DataFrame
        data = [item.dict() for item in result.__root__]
        df = pd.DataFrame(data)
        print("dataframe:",df)
        return df
    except ValidationError as e:
        print("Validation error:", e)
        return pd.DataFrame()  # Return an empty DataFrame in case of validation errors

    except Exception as e:
        print("Error:", e)
        return pd.DataFrame()  # Return an empty DataFrame in case of other errors



###############################################################################################

##creating plotly graphs

async def plot_charts(df, chart_type):
    """
    Generate Plotly charts (bar, line, pie) based on the provided DataFrame.
    """
    print("plot chart started")
    if chart_type == 'bar':
        filtered_df = df[~df['Category'].isin(['Breakeven Analysis', 'ROI Calculation'])]
        fig = px.bar(
            filtered_df,
            x='Category',
            y='Cost',
            color='Component',
            title='Cost Distribution by the Category and Component',
            text='Cost',
            barmode='group',
            text_auto=True,
        )
        print("before fig update")
        fig.update_layout(
            yaxis_title="Cost ($)",
            xaxis_title="Category",
            legend_title='Component'
        )
        fig.update_traces(
            width=0.60,
            opacity=0.8
        )
        
        # Send chart as a separate message without content
        await cl.Message(
            content="",  # Empty content to avoid expandable section
            elements=[
                cl.Plotly(name="chart", figure=fig, display="inline", size="large")
            ]
        ).send()


async def process_idea():
    print("Processing user idea.")
    await send_message("Thank you for sharing your idea.")
    response = await ask_action("Are you ready to answer a few questions to understand the case?", ["yes", "no"])
    if response == "yes":
        runnable = cl.user_session.get("runnable")
        # Use await for asynchronous execution to ensure completion
        content = await runnable.ainvoke({"input": user_idea})
        try:
            cleaned_content = content.strip().strip('```json').strip('```').strip()
            questions = json.loads(cleaned_content)
            print(f"Questions generated: {questions}")
            print("User is ready to answer questions.")
            await ask_question(0, questions)
        except json.JSONDecodeError as e:
            logging.error(f"Error decoding JSON: {e}")
            questions = []
    else:
        global ans
        ans = await create_business_case()
        save_case = await ask_action("Would you like to save your report or refine them a bit further?", ["I would like to save", "Let me ask somethings a bit further"])
        if save_case == "I would like to save":
            global item_id
            item_id = await save_case_generated(user_idea, ans, item_id)
            await send_message('Your Case has been saved') if item_id is not None else send_message('There has been an error saving your message, hold on...')
    def clean_numeric(cls, value):
        if isinstance(value, str):
            #remove $ and , characters
            cleaned_value = value.replace("$", "").replace(",", "").strip()
            
            # Handling percentages by removing % and converting to float
            if "%" in cleaned_value:
                return float(cleaned_value.replace("%", "").strip())
            try:
                ##convert the clean value to an int
                return int(cleaned_value)
            except ValueError:
                raise ValueError(f"Invalid cost value: {value}")
        return value

class RoiTableList(BaseModel):
    __root__: List[RoiTableSchema]


async def parse_markdown_to_dataframe(response: str):
    """
    Parses a markdown response into a DataFrame.

    Args:
        response (str): The markdown text to parse.

    Returns:
        pd.DataFrame: A DataFrame containing the parsed data.

    Raises:
        ValidationError: If the response fails validation.
        Exception: For any other processing errors.
    """
    # Define the PydanticOutputParser and PromptTemplate logic here
    parser = PydanticOutputParser(pydantic_object=RoiTableList)

    prompt = PromptTemplate(
        template=(
            "Extract the ROI Analysis table from the markdown input and return each row as JSON."
            "Ensure the keys match this structure: 'Category', 'Component', 'Cost', 'Calculations', 'Assumptions'."
            "Ensure numeric fields (Cost, Break_even_months) are integers without formatting (no $ or commas).\n"
            "{markdown_input}\n"
        ),
        input_variables=["markdown_input"],
    )

    # Use global ai_model instead of model
    chain = prompt | ai_model | parser

    try:
        # Process the markdown input through the chain
        result = await chain.ainvoke({"markdown_input": response})
        
        # Ensure the result is a list
        if isinstance(result, dict):
            result = [result]  # Wrap single dict in a list


        # Convert result to a DataFrame
        data = [item.dict() for item in result.__root__]
        df = pd.DataFrame(data)
        print("dataframe:",df)
        return df
    except ValidationError as e:
        print("Validation error:", e)
        return pd.DataFrame()  # Return an empty DataFrame in case of validation errors

    except Exception as e:
        print("Error:", e)
        return pd.DataFrame()  # Return an empty DataFrame in case of other errors



###############################################################################################

##creating plotly graphs

async def plot_charts(df, chart_type):
    """
    Generate Plotly charts (bar, line, pie) based on the provided DataFrame.
    """
    print("plot chart started")
    if chart_type == 'bar':
        filtered_df = df[~df['Category'].isin(['Breakeven Analysis', 'ROI Calculation'])]
        fig = px.bar(
            filtered_df,
            x='Category',
            y='Cost',
            color='Component',
            title='Cost Distribution by the Category and Component',
            text='Cost',
            barmode='group',
            text_auto=True,
        )
        print("before fig update")
        fig.update_layout(
            yaxis_title="Cost ($)",
            xaxis_title="Category",
            legend_title='Component'
        )
        fig.update_traces(
            width=0.60,
            opacity=0.8
        )
        
        # Send chart as a separate message without content
        await cl.Message(
            content="",  # Empty content to avoid expandable section
            elements=[
                cl.Plotly(name="chart", figure=fig, display="inline", size="large")
            ]
        ).send()


