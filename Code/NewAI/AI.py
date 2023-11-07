import os
from time import sleep
from typing import Any, Optional
from dotenv import load_dotenv, find_dotenv

import openai
from prompts import SystemPrompt
import tiktoken
from termcolor import colored

load_dotenv(find_dotenv())
if os.getenv("OPENAI_ORGANIZATION") is not None:
    openai.organization = os.getenv("OPENAI_ORGANIZATION")
openai.api_key = os.getenv("OPENAI_API_KEY")

defaultModels = {
    "gpt-3.5-turbo": 4095,
    "gpt-3.5-turbo-16k": 16384
}


class Ai:
    def __init__(self, models=defaultModels, temperature=0.5, maxAttempts=3, verbose=True,  systemMessage=SystemPrompt()):
        self.models = models
        self.temperature = temperature
        self.maxAttempts = maxAttempts
        self.verbose = verbose
        self.messages = systemMessage.getSytemPrompt()

    def clearMessages(self, newSystemMessage=SystemPrompt()):
        self.messages = newSystemMessage.getSytemPrompt()

    def removeMessagesUntillShortEnough(self, model, newTokens=0):
        tokens = self.num_tokens_from_messages(
            self.messages, model, newTokens)
        while tokens > self.models[model]:
            startPopFrom = 0 if self.messages[0]["role"] == "user" else 1
            if len(self.messages) > 1:
                self.messages.pop(startPopFrom)
                self.messages.pop(startPopFrom)
                # pops twice because it should pop a pair of request response messages and pops 1 because it shouldn't pop system prompt
            else:
                break
            tokens = self.num_tokens_from_messages(
                self.messages, model, newTokens)
        else:
            return
        if self.verbose:
            print("Removed all messages possible and still too long, Can't do it")
        raise RuntimeError(
            "Removed all messages possible and still too long, Can't do it")

    def getAIOutput(self, model) -> dict[Any, Any] | None:
        for i in range(self.maxAttempts):
            try:
                response = openai.ChatCompletion.create(  # ignore
                    model=model, messages=self.messages, temperature=self.temperature)  # ignore
                if self.verbose:
                    print("asked ai and got ", response)
                assert isinstance(response, dict)
                return response
            except openai.error.RateLimitError as e:  # type: ignore
                print(
                    f"TOO MANY REQUESTS. waiting and trying again\n OpenAi says {e}")
                sleep(self.determineWait(currentTry=i+1))
                continue
            except Exception as e:
                print(f"OpenAi Error: {e}")
                sleep(self.determineWait(currentTry=i+1))
                continue

        if self.verbose:
            print(
                f"Failed to get response from AI after {self.maxAttempts} attempts.")
        return None

    # possibility of it being stuck in an infinite loop in the case that it doesn't get to finish and the just input is still below the limit
    def AskAI(self, newMessage: str, model=None):
        if self.verbose:
            print(f"Asking AI: {newMessage}")
        finished = False
        newTokens = 0
        response = None
        while not finished:
            # the ternary statement is because once we have already added the response to the list once we don't want to continue to add it again
            messageToPass = newMessage if newTokens == 0 else None
            model = self.prepAIRequest(
                messageToPass, model, newTokens=newTokens)
            response = self.getAIOutput(model)
            if response is None:
                return None
            finished = self.assertGotToFinish(response)
            newTokens = response["usage"]["completion_tokens"]
        responseContent = self.extractResponse(
            response=response)
        if self.verbose:
            print("message 6, got response text", responseContent)
        self.messages.append(self.formatTextAsMessage(
            responseContent, role="assistant"))
        return response

    def prepAIRequest(self, newMessage, model, newTokens=0):
        if newMessage is not None:
            self.messages.append(
                self.formatTextAsMessage(newMessage, role="user"))
        if model is None:
            model = list(self.models.keys())[0]
        tokens = self.num_tokens_from_messages(
            self.messages, model, newTokens=newTokens)
        if self.verbose:
            print(f"tokens: {tokens}")
            self.pretty_print_conversation()
        model = self.ChangeModelUntillLargeEnough(model, tokens)
        if tokens > self.models[model]:
            if self.verbose:
                print(
                    f"Too many tokens ({tokens}) for {model} removing oldest messages untill we are under the limit.")
            self.removeMessagesUntillShortEnough(model, newTokens=newTokens)
        return model

    def ChangeModelUntillLargeEnough(self, model, tokens):
        for i in range(list(self.models.keys()).index(model), len(list(self.models.keys()))):
            model = list(self.models.keys())[i]
            if tokens <= self.models[model]:
                break
            if self.verbose:
                print(
                    f"Too many tokens ({tokens}) for {model}. Switching to next model.")
        return model

    # Not finished
    def assertGotToFinish(self, response):
        # type: ignore
        return response["choices"][0]["finish_reason"] == "stop"

    def determineWait(self, currentTry, maxTries=None, waitTime=30, factor=2) -> int:
        if maxTries is None:
            maxTries = self.maxAttempts
        initialWait = (waitTime*(1-factor))/(1-factor**maxTries)
        currentWait = initialWait*factor**(currentTry-1)
        assert currentWait <= waitTime
        return currentWait

    def extractResponse(self, response=None) -> str:
        if self.verbose:
            print("extracting response")
        if response is None:
            if len(self.messages) == 0:
                raise RuntimeError("No messages to extract response from")
            response = self.messages[-1]
        return response["choices"][0]["message"]["content"]

    def formatTextAsMessage(self, text: str, role: str = "user", name: Optional[str] = None) -> "dict[str,Any]":
        message: dict[str, str] = {
            "role": role,
            "content": text
        }
        if name:
            message["name"] = name
        return message

    def num_tokens_from_messages(self, messages, model, newTokens=0):
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
            return self.num_tokens_from_messages(messages, model="gpt-3.5-turbo-0613", newTokens=newTokens)
        elif "gpt-4" in model:
            return self.num_tokens_from_messages(messages, model="gpt-4-0613", newTokens=newTokens)
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
        return num_tokens + newTokens

    def getMessages(self) -> list[dict[str, str]]:
        return self.messages

    def pretty_print_conversation(self):
        print("printing conversation\n\n")
        role_to_color: dict[str, str] = {
            "system": "red",
            "user": "green",
            "assistant": "blue",
            "function": "magenta",
        }

        for message in self.messages:
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
