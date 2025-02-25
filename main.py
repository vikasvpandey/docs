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

from typing import List, Optional, Union, cast
from langchain.output_parsers import PydanticOutputParser
from langchain_core.prompts import PromptTemplate
from langchain_core.pydantic_v1 import BaseModel, ValidationError, Field, validator
import plotly.express as px
import plotly.graph_objects as go
from helper import save_case_generated


env = AppConfig()
ai_model = AzureAI(env).get_client()
questions = []
answers = []
user_idea = ""
item_id = None

async def initialize_memory():
    print("Initializing conversation memory.")
    cl.user_session.set("memory", ConversationBufferMemory(return_messages=True))
    global answers, user_idea
    answers = []
    user_idea = ""
    # ... existing code ...

async def ask_action(content, options):
    # ... existing code ...

async def ask_user_message(content, timeout=20):
    # ... existing code ...

async def ask_user_message_for_idea(content):
    # ... existing code ...

async def send_message(content):
    # ... existing code ...

async def create_runnable(prompt, input_key):
    # ... existing code ...

@cl.on_chat_start
async def on_chat_start():
    # ... existing code ...

@cl.on_message
async def on_message(message: cl.Message):
    # ... existing code ...

async def process_idea():
    # ... existing code ...

async def ask_question(index:int, questions: list):
    # ... existing code ...

async def on_answer(questions: list, index: int, answer: list):
    # ... existing code ...

async def on_cancel(questions: list, index: int):
    # ... existing code ...

async def ask_remaining_questions(remaining_questions: list):
    # ... existing code ...

async def create_business_case():
    # ... existing code ...

async def send_to_llm(input_data):
    # ... existing code ...

class RoiTableSchema(BaseModel):
    # ... existing code ...

class RoiTableList(BaseModel):
    __root__: List[RoiTableSchema]

async def parse_markdown_to_dataframe(response: str):
    # ... existing code ...

async def plot_charts(df, chart_type):
    # ... existing code ...

def sum(a, b):
    """
    Enhanced sum function to handle non-numeric inputs, None values, and edge cases.
    """
    if a is None or b is None:
        raise ValueError("Both parameters must not be None.")
    if not isinstance(a, (int, float)) or not isinstance(b, (int, float)):
        raise ValueError("Both parameters must be numeric.")
    return a + b
