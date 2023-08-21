from time import sleep
from typing import Optional, Any
from dotenv import load_dotenv, find_dotenv
import os
import openai
import json
from sympy import true
import tiktoken
from prompts import booleanPrompt, MQLPrompt, fixJSONPrompt, BackgroundPrompt
from termcolor import colored

# from dotenv import load_dotenv, find_dotenv
# load_dotenv(find_dotenv())

GPTmodel = "gpt-3.5-turbo"
longerContextModel = "gpt-3.5-turbo-16k"
contextLimits: dict[str, int] = {
    "gpt-3.5-turbo": 4095,
    "gpt-3.5-turbo-16k": 16383
}

load_dotenv(find_dotenv())
openai.api_key = os.getenv("OPENAI_API_KEY")


def AskAI(text: str, prompt: Optional[BackgroundPrompt] = None, model: str = GPTmodel, longerContextModel: str = longerContextModel, temperature: float = 0, maxAttempts: int = 3, verbose: bool = True) -> Optional[str]:
    print("ASKING AI")
    allMessages: list[dict[str, Any]] = []
    if prompt is not None:
        allMessages += prompt.messages
    allMessages.append(formatTextAsMessage(text, role="user"))

    i = 0
    response = None
    tokens = num_tokens_from_messages(allMessages, model)
    if tokens >= contextLimits[model]:
        if verbose:
            print(
                f"Too many tokens ({tokens}) for {model}. Switching to {longerContextModel}.")
        model = longerContextModel
        tokens = num_tokens_from_messages(allMessages, model)
        if tokens >= contextLimits[model]:
            print(colored(
                text=f"Too many tokens ({tokens}) for larger model: {model}. Please reduce the number of messages in the prompt.", color="cyan"))
    for i in range(maxAttempts):
        try:
            response = openai.ChatCompletion.create(  # ignore
                model=model, messages=allMessages, temperature=temperature)  # ignore
            break
        except openai.error.RateLimitError as e:  # type: ignore
            print(
                f"TOO MANY REQUESTS. waiting and trying again\n OpenAi says {e.wait}")
            sleep(determineWait(maxTries=maxAttempts, waitTime=60, currentTry=i+1))
            continue
        except Exception as e:
            print(f"OpenAi Error: {e}")
            sleep(determineWait(maxTries=maxAttempts, waitTime=60, currentTry=i+1))
            continue

    if i == maxAttempts-1:
        print(f"Failed to get response from AI after {maxAttempts} attempts.")
        return None

    assert response
    if verbose:
        allMessages.append(formatTextAsMessage(
            extractResponse(response=response), role="assistant"))
        pretty_print_conversation(messages=allMessages)

    return extractResponse(response)


# this function uses the geometric sum formula to calculate how much to wait between attempts while ensuring that by its last attempt it would have tried to wait the max wait, and then one more time after that waiting a full minute
def determineWait(maxTries, waitTime, currentTry, factor=2) -> int:
    initialWait = (waitTime*(1-factor))/(1-factor**maxTries)
    currentWait = initialWait*factor**(currentTry-1)
    return currentWait


def extractResponse(response) -> str:
    return response["choices"][0]["message"]["content"]


def formatTextAsMessage(text: str, role: str = "user", name: Optional[str] = None) -> "dict[str,Any]":
    message: dict[str, str] = {
        "role": role,
        "content": text
    }
    if name:
        message["name"] = name
    return message


def ConvertTextToBool(text: str, model: str = GPTmodel, temperature: float = 0, verbose: bool = True) -> Optional[str]:
    print("converting text to bool")
    return AskAI(prompt=booleanPrompt, text=text, model=model, temperature=temperature, verbose=verbose)


def ConvertBoolToMQL(text: str, model: str = GPTmodel, temperature: float = 0, verbose: bool = True) -> Optional[str]:
    print("converting bool to MQL")
    return AskAI(prompt=MQLPrompt, text=text, model=model, temperature=temperature, verbose=verbose)


def TranslateTextToMQL(TextEligibility: str, jsonTries: int = 3) -> Any | None:
    listFormat: str | None = ConvertTextToBool(TextEligibility)
    if listFormat is None:
        print("Could not convert to list")
        return None
    MQL: str | None = ConvertBoolToMQL(listFormat)
    if MQL is None:
        print("Could not convert to MQL")
        return None
    ProperMQL: Any | None = fixJSON(MQL, jsonTries)
    return ProperMQL


def fixJSON(text: str, tries: int = 3, maxTemperature: float = 1) -> Any | None:
    print("fixing json")
    jsonText = text
    jsonAttempt = None

    try:
        jsonAttempt = json.loads(jsonText)
        print("JSON is valid, does not need fixing")
        return jsonAttempt
    except:
        print("Your json is not valid, attempting to fix it.")

    for i in range(tries):
        temperature: float = i*(maxTemperature/(tries-1))
        assert jsonText
        jsonText = AskAI(prompt=fixJSONPrompt, text=jsonText,
                         temperature=temperature)
        if jsonText is None:
            print(
                f"\n\n\nAttempt {i+1} at a temperature of {temperature} Failed to  correct json. \n\n Attempt resulted in OpenAi failing\n\n\n\n\n")
            continue
        try:
            jsonAttempt = json.loads(jsonText)
            print(
                f"Attempt {i+1} at a temperature of {temperature} succeeded in correcting json. \n\n Attempt resulted in\n\n{jsonText}\n\n\n")
            return jsonAttempt
        except:
            print(
                f"\n\n\nAttempt {i+1} at a temperature of {temperature} Failed to  correct json. \n\n Attempt resulted in\n\n{jsonText}\n\n\nGetting a bit wilder and trying again")

    print(f"\n\n\nFailed to convert to json\n\n")
    return None


def num_tokens_from_messages(messages, model):
    """Return the number of tokens used by a list of messages."""
    try:
        encoding = tiktoken.encoding_for_model(model)
    except KeyError:
        print("Warning: model not found. Using cl100k_base encoding.")
        encoding = tiktoken.get_encoding("cl100k_base")
    if model in {
        "gpt-3.5-turbo-0613",
        "gpt-3.5-turbo-16k-0613",
        "gpt-4-0314",
        "gpt-4-32k-0314",
        "gpt-4-0613",
        "gpt-4-32k-0613",
    }:
        tokens_per_message = 3
        tokens_per_name = 1
    elif model == "gpt-3.5-turbo-0301":
        # every message follows <|start|>{role/name}\n{content}<|end|>\n
        tokens_per_message = 4
        tokens_per_name = -1  # if there's a name, the role is omitted
    elif "gpt-3.5-turbo" in model:
        return num_tokens_from_messages(messages, model="gpt-3.5-turbo-0613")
    elif "gpt-4" in model:
        return num_tokens_from_messages(messages, model="gpt-4-0613")
    else:
        raise NotImplementedError(
            f"""num_tokens_from_messages() is not implemented for model {model}. See https://github.com/openai/openai-python/blob/main/chatml.md for information on how messages are converted to tokens."""
        )
    num_tokens = 0
    for message in messages:
        num_tokens += tokens_per_message
        for key, value in message.items():
            num_tokens += len(encoding.encode(value))
            if key == "name":
                num_tokens += tokens_per_name
    num_tokens += 3  # every reply is primed with <|start|>assistant<|message|>
    return num_tokens


def pretty_print_conversation(messages: "list[dict[str, str]]"):
    print("printing conversation\n\n")
    role_to_color: dict[str, str] = {
        "system": "red",
        "user": "green",
        "assistant": "blue",
        "function": "magenta",
    }

    for message in messages:
        if message["role"] == "system":
            print(
                colored(f"system: {message['content']}\n", role_to_color[message["role"]]))
        elif message["role"] == "user":
            print(
                colored(f"user: {message['content']}\n", role_to_color[message["role"]]))
        elif message["role"] == "assistant" and message.get("function_call"):
            print(colored(
                f"assistant: {message['function_call']}\n", role_to_color[message["role"]]))
        elif message["role"] == "assistant" and not message.get("function_call"):
            print(
                colored(f"assistant: {message['content']}\n", role_to_color[message["role"]]))
        elif message["role"] == "function":
            print(colored(
                f"function ({message['name']}): {message['content']}\n", role_to_color[message["role"]]))
