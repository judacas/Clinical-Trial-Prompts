from langchain.schema import (
    AIMessage,
    HumanMessage,
    SystemMessage
)

from langchain.llms import OpenAI
from langchain import PromptTemplate

from dotenv import load_dotenv, find_dotenv
load_dotenv(find_dotenv())


llm = OpenAI(model_name="text-davinci-003", temperature=0.8)  # type: ignore


# chat = ChatOpenAI(model_name="gpt-3.5-turbo", temperature=0.3)
# messages = [
#     SystemMessage(
#         content="You are an expert summarizer and never change the meaning of the text you are summarizing"),
#     HumanMessage(
#         content="Write a Python script that trains a neural network on simulated data ")
# ]


def GetDescription(level: str, clinicalTrial: str) -> str:
    descriptionTemplate = "You will be given a json containing information about a clinical trial. you will provide a one paragraph summary that a {level} can understand. Do not change any of the facts, you must not alter any of the meanings. the clinical trial json is as follows: {clinicalTrial}"
    descriptionPrompt = PromptTemplate.from_template(descriptionTemplate)

    return descriptionPrompt.format(level=level, clinicalTrial=clinicalTrial)
