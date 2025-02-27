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


#plotting
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
    actions = [cl.Action(name=option, value=option.capitalize()) for option in options]
    response = await cl.AskActionMessage(content=content, actions=actions).send()

    if response:
        return response.get("name")
    else:
        return "No"

async def ask_user_message(content, timeout=20):
    print(f"Asking user message: {content} with timeout: {timeout}")
    # Correcting this part where the message is incorrectly added to chat memory
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
    # Use global model instead of creating a new instance
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

async def process_idea():
    print("Processing user idea.")
    await send_message("Thank you for sharing your idea.")
    response = await ask_action("Are you ready to answer a few questions to understand the case?", ["yes", "no"])
    if response == "yes":
        runnable = cl.user_session.get("runnable")
        try:
            content = runnable.invoke({"input": user_idea})
            # Adding more verbose error logging including content
            cleaned_content = content.strip().strip('```json').strip('```').strip()
            questions = json.loads(cleaned_content)
            print(f"Questions generated: {questions}")
            print("User is ready to answer questions.")
            await ask_question(0, questions)
        except json.JSONDecodeError as e:
            logging.error(f"Error decoding JSON: {e}, content: {content}")  # Add more details here
            questions = []
    else:
        global ans
        ans = await create_business_case()
        save_case = await ask_action("Would you like to save your report or refine them a bit further?", ["I would like to save", "Let me ask somethings a bit further"])
        if save_case == "I would like to save":
            global item_id
            item_id = await save_case_generated(user_idea, ans, item_id)
            await send_message('Your Case has been saved') if item_id else await send_message('There has been an error saving your message, hold on...')

async def ask_question(index: int, questions: list):
    '''
    Handles asking questions to users and processing their responses.
    '''
    // ... existing code ...

async def on_answer(questions: list, index: int, answer: list):
    '''
    Process the answer given by the user for a particular question.
    '''
    // ... existing code ...

async def on_cancel(questions: list, index: int):
    '''
    Handles the situation when user cancels answering questions.
    '''
    // ... existing code ...

// ... existing code for other functions ...
