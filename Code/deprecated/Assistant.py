
import json
import os
import time
from typing import Any

from dotenv import find_dotenv, load_dotenv
from openai import OpenAI
from termcolor import colored

load_dotenv(find_dotenv())
apiKey = os.getenv("OPENAI_API_KEY")
organization = os.getenv("OPENAI_ORGANIZATION_ID")
# trunk-ignore(bandit/B101)
assert apiKey is not None
client = OpenAI(api_key=apiKey, organization=organization)
ttbID = os.getenv("CriteriaBooleanTranslatorID")
infoGatherID = os.getenv("InformationGathererID")
with open("../Prompts/TextToBooleanExpression.txt", "r") as file:
    ttbPrompt = file.read()


# TODO: This code definitely needs to be refactored. It's a mess.
# TODO: Update to v2 API for openAI


def show_json(obj :Any) -> None:
    if isinstance(obj, str):
        obj = json.loads(obj)
    print(json.dumps(json.loads(obj.model_dump_json()), indent=4))
    

def getAssistantObj(assistantID = None):
    if assistantID is None:
        return client.beta.assistants.create(model="gpt-4o")
    return client.beta.assistants.retrieve(assistant_id=assistantID)

def getThreadObj(threadID= None):
    if threadID is None:
        return client.beta.threads.create()
    return client.beta.threads.retrieve(thread_id=threadID)


def assertThread(thread = None):
    return getThreadObj(thread) if (isinstance(thread, str) or thread is None) else thread

def assertAssistant(assistant = None):
    return getAssistantObj(assistant) if (isinstance(assistant, str) or assistant is None) else assistant



def run(assistant = None, thread=None, wait :bool=True, newMsg :str ="", verbose :bool =False):
    newMsg = str(newMsg).strip()
    assistant = assertAssistant(assistant)
    thread = assertThread(thread)
    if newMsg != "":
        client.beta.threads.messages.create(
            thread_id=thread.id, role="user", content=newMsg
        )
        run = client.beta.threads.runs.create(
            thread_id=thread.id, assistant_id=assistant.id
        )


    if wait:
        return waitForRun(run, verbose=verbose)
    if verbose:
        print(f"resulted in {getResponse(run.thread_id)}")
    return run

def getFunctionCall(threadID:str, runID: str)->dict[str, Any]:
    run = client.beta.threads.runs.retrieve(
        thread_id=threadID,
        run_id=runID,
    )
    assert run.required_action is not None
    functionCall: dict[str, Any] = run.required_action.submit_tool_outputs.model_dump()
    print(functionCall)
    return functionCall

def getRun(threadID:str, runID: str):
        return client.beta.threads.runs.retrieve(
            thread_id=threadID,
            run_id=runID,
        )

def waitForRun(run, verbose :bool =False):
    while run.status == "queued" or run.status == "in_progress":
        time.sleep(0.5)
        run = client.beta.threads.runs.retrieve(
            thread_id=run.thread_id,
            run_id=run.id,
        )
        if verbose:
            print(f"Run status: {run.status}")
    if verbose:
        print(f"resulted in {getResponse(run.thread_id)}")
    return run


def getMessages(thread):
    thread = assertThread(thread)
    return client.beta.threads.messages.list(thread_id=thread.id)

# unused
def getMessagesTextOnly(thread):
    thread = assertThread(thread)
    messages = getMessages(thread.id)
    return [m.content[0].text.value for m in messages] # type: ignore

def getResponse(thread)-> str:
    thread = assertThread(thread)
    return list(getMessages(thread.id))[0].content[0].text.value # type: ignore

def runAndGetResponse(assistant = None, thread=None, wait :bool=True, newMsg :str ="", verbose :bool =False):
    assistant = assertAssistant(assistant)
    thread = assertThread(thread)
    run(assistant=assistant, thread=thread, wait=wait, newMsg=newMsg, verbose=verbose)
    return getResponse(thread=thread)

def pretty_print(messages):
    print(colored("# Messages", "yellow"))
    for m in messages:
        role = m.role
        if role == "user":
            role_color = "green"
        elif role == "assistant":
            role_color = "red"
        else:
            role_color = "white"
        print(colored(f"{role}: {m.content[0].text.value}\n", role_color)) 
    print()