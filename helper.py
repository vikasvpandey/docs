
from appconfig import AppConfig
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
import httpx
env = AppConfig()

async def initialize_memory():
    print("Initializing conversation memory.")
    cl.user_session.set("memory", ConversationBufferMemory(return_messages=True))
    # Reset global variables
    global questions, answers, user_idea
    questions = []
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

async def ask_user_message(content, timeout=120):
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
    model = AzureAI(env).get_client()
    return prompt | model | StrOutputParser()


async def save_case_generated(user_idea: str, case_generated: str, item_id):
    request_body = {
            "user_idea": user_idea,
            "case_generated": case_generated
        }

    headers = {
            "Content-Type": "application/json",
            "Accept": "application/json"
        }

    async with httpx.AsyncClient() as client:
            try:
                if item_id is not None:
                    response = await client.put(
                        url=f"https://maas-friendly-gnu-ca.cfapps.eu10-004.hana.ondemand.com/commercialCases/{item_id}",
                        headers=headers,
                        json=request_body)
                else:
                    response = await client.post(
                        url="https://maas-friendly-gnu-ca.cfapps.eu10-004.hana.ondemand.com/commercialCases",
                        headers=headers,
                        json=request_body)

                if response.status_code == 307:
                    redirect_url = response.headers.get("Location")
                    if redirect_url:
                        print(f"Redirected to: {redirect_url}")
                        response = await client.post(
                            url=redirect_url,
                            headers=headers,
                            json=request_body
                        )
                    # Checking response status and parsing JSON
                if response.is_success:  # Adjust the success code if needed
                    try:
                        response_data = response.json()
                        print(f"Response has been obtained {response.status_code} with Item ID {response_data.get('id')}")
                        return response_data.get('id')
                    except ValueError:
                        print("Response is not valid JSON.")
                        return None
                                                
            except httpx.RequestError as e:
                print(f"An error occurred while requesting: {e}")
                return None
