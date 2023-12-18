import json
import os
import time
from typing import Any, Dict, List

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
currentAssistantID = os.getenv("ClinicalTrialAssistantID")
currentThreadID = os.getenv("CurrentThreadID")


def show_json(obj :Any) -> None:
    print(json.dumps(json.loads(obj.model_dump_json()), indent=4))


def run(assistant, thread=None, wait :bool=True, newMsg :str =""):

    if thread is None:
        thread = client.beta.threads.create()
    if newMsg != "":
        client.beta.threads.messages.create(
            thread_id=thread.id, role="user", content=newMsg
        )

    run = client.beta.threads.runs.create(
        thread_id=thread.id, assistant_id=assistant.id
    )

    if wait:
        waitForRun(run, thread)


def waitForRun(run, thread):
    while run.status == "queued" or run.status == "in_progress":
        run = client.beta.threads.runs.retrieve(
            thread_id=thread.id,
            run_id=run.id,
        )
        print(f"Run status: {run.status}")
        time.sleep(0.5)

    return run


def getMessages(threadID :str):
    return client.beta.threads.messages.list(thread_id=threadID)


def pretty_print(messages: List[Dict[str, Any]]):
    print(colored("# Messages", "yellow"))
    for m in messages:
        role = m.role # type: ignore
        if role == "user":
            role_color = "green"
        elif role == "assistant":
            role_color = "red"
        else:
            role_color = "white"
        print(colored(f"{role}: {m.content[0].text.value}\n", role_color)) # type: ignore
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


# pretty_print(getMessages("thread_4iajCxDX6aJdh5lQ78w6Xer1"))
removeThreadID("this is yet another test")
activeThreads = getActiveThreads()
if activeThreads is not None:
    for thread in activeThreads:
        print(thread)
