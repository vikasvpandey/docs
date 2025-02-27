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

// ... existing code ...

async def process_idea():
    print("Processing user idea.")
    await send_message("Thank you for sharing your idea.")
    response = await ask_action("Are you ready to answer a few questions to understand the case?", ["yes", "no"])
    if response == "yes":
        runnable = cl.user_session.get("runnable")
        content = await runnable.ainvoke({"input": user_idea})  # Changed synchronous call to async
        try:
            cleaned_content = content.strip().strip('```json').strip('```').strip()
            questions = json.loads(cleaned_content)
            print(f"Questions generated: {questions}")
            print("User is ready to answer questions.")
            await ask_question(0, questions)
        except json.JSONDecodeError as e:
            logging.error(f"Error decoding JSON: {e}")
            questions = []  # Ensure questions variable is set
            await send_message("Unable to process questions. Please try again later.")
    else:
        global ans
        ans = await create_business_case()
        save_case = await ask_action("Would you like to save your report or refine them a bit further?", ["I would like to save", "Let me ask somethings a bit further"])
        if save_case == "I would like to save":
            global item_id
            item_id = await save_case_generated(user_idea, ans, item_id)
            await send_message('Your Case has been saved') if item_id is not None else send_message('There has been an error saving your message, hold on...')

// ... existing code ...