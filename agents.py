
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
from agents import run_group_chat


# Set log level to DEBUG for detailed logging
# logging.basicConfig(level=logging.DEBUG)

# Environment configuration
env = AppConfig()
# Initialize Azure AI model as a global variable
ai_model = AzureAI(env).get_client_llm()
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
    actions = [
        cl.Action(
            name=option,
            value=option,
            description=option.capitalize(),
            payload={"option": option}  # Ensure payload is included
        ) for option in options
    ]    
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
                ("system","analyze user input provided, and if you need additional details ask questions as per"+ env.CHAT_PROMPT_TEMPLATE + " Ensure the JSON response is as below: [{{\"question\": <question>}}]"),
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
        await send_message("Creating business case. Please wait")
        
        # Prepare input for agents using collected data
        business_case_query = f"""
        User Idea: {user_idea}
        Collected Answers:
        {json.dumps(answers, indent=2)}
        
        Please analyze this business case and provide:
        1. Comprehensive market analysis
        2. Effort estimation and resource planning
        3. Financial projections and ROI analysis
        """

        # Use agentic framework instead of direct LLM call
        agent_responses = await run_group_chat(business_case_query)
        
        # Send each agent response as message
        for response in agent_responses:
            await cl.Message(content=response).send()
            print("Agent Response:", response)

    except Exception as err:
        print(f"An error occurred: {err}")




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


