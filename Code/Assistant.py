import json
import os
import time
from typing import Any

import dotenv
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
with open("Code\\PostDevDayAI\\TextToBoolPrompt.txt", "r") as file:
    ttbPrompt = file.read()



def show_json(obj :Any) -> None:
    if isinstance(obj, str):
        obj = json.loads(obj)
    print(json.dumps(json.loads(obj.model_dump_json()), indent=4))
    

def getAssistantObj(assistantID = None):
    if assistantID is None:
        return client.beta.assistants.create(model="gpt-4-1106-preview")
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


 
    


def addThreadID(threadID :str) -> None:
    # Read the current thread IDs
    dotenvPath = dotenv.find_dotenv()
    with open(dotenvPath, "r") as file:
        lines = file.readlines()

    # Find the line with ActiveThreads and append the new thread ID
    for i, line in enumerate(lines):
        if line.startswith("ActiveThreads"):
            # If there's already a list, append to it
            if line.strip() != 'ActiveThreads=""':
                lines[i] = line[:-2] + "," + threadID + '"\n'
            # If there's no list yet, create one
            else:
                lines[i] = 'ActiveThreads="' + threadID + '"\n'
            break
    else:
        # If ActiveThreads is not in the file, add it
        lines.append('\nActiveThreads="' + threadID + '"\n')

    # Write the updated lines back to the file
    with open(dotenvPath, "w") as file:
        file.writelines(lines)


def getActiveThreads() -> list[str] | None:
    # Find the .env file
    dotenvPath: str = find_dotenv()
    if dotenvPath== "":
        print("Could not find .env file")
        return

    # Read the .env file
    with open(dotenvPath, "r") as file:
        lines = file.readlines()

    # Find the line with ActiveThreads
    for line in lines:
        if line.startswith("ActiveThreads"):
            # Get the list of active threads
            active_threads = line.split("=")[1].strip().strip('"').split(",")
            return active_threads

    # If ActiveThreads is not in the file, return an empty list
    return


def removeThreadID(threadID :str) -> None:
    # Find the .env file
    dotenvPath: str = find_dotenv()
    if dotenvPath == "":
        print("Could not find .env file")
        return

    # Get the list of active threads
    activeThreads: list[str] | None = getActiveThreads()
    if activeThreads is None:
        print("Could not find ActiveThreads in .env file")
        return

    # Remove the thread from the list
    if threadID in activeThreads:
        activeThreads.remove(threadID)
        

    # Write the updated list back to the file
    with open(dotenvPath, "r") as file:
        lines = file.readlines()

    for i, line in enumerate(lines):
        if line.startswith("ActiveThreads"):
            lines[i] = 'ActiveThreads="' + ",".join(activeThreads) + '"\n'
            break

    with open(dotenvPath, "w") as file:
        file.writelines(lines)

# print(run(newMsg="this is a test", verbose=True))
# pretty_print(messages=client.beta.threads.messages.list(thread_id="thread_ZuoErUMPUOwTlxtViCPTM8Qd"))
# print(getResponse(thread=client.beta.threads.retrieve(thread_id="thread_ZuoErUMPUOwTlxtViCPTM8Qd")))


# # pretty_print(getMessages("thread_4iajCxDX6aJdh5lQ78w6Xer1"))
# removeThreadID("this is yet another test")
# activeThreads = getActiveThreads()
# if activeThreads is not None:
#     for thread in activeThreads:
#         print(thread)
