import os
import openai
import json
from prompts import booleanPrompt, MQLPrompt, fixJSONPrompt, BackgroundPrompt
from termcolor import colored

# from dotenv import load_dotenv, find_dotenv
# load_dotenv(find_dotenv())

GPTmodel = "gpt-3.5-turbo-16k"


openai.api_key = os.getenv("OPENAI_API_KEY")


def AskAI(prompt: BackgroundPrompt, text: str, model: str = GPTmodel, temperature: float = 0, verbose: bool = True) -> str:
    allMessages = prompt.messages
    allMessages.append(text)
    response = openai.ChatCompletion.create(
        model=model, messages=allMessages, temperature=temperature, verbose=verbose)

    return response.choices[0]["message"]["content"]


def ConvertTextToBool(text: str, model: str = GPTmodel, temperature: float = 0, verbose: bool = True) -> str:
    return AskAI(prompt=booleanPrompt, text=text, model=model, temperature=temperature, verbose=verbose)


def ConvertBoolToMQL(text: str, model: str = GPTmodel, temperature: float = 0, verbose: bool = True) -> str:
    return AskAI(prompt=MQLPrompt, text=text, model=model, temperature=temperature, verbose=verbose)


def TranslateTextToMQL(TextEligibility, jsonTries: int = 3):
    listFormat = ConvertTextToBool(TextEligibility)
    MQL = ConvertBoolToMQL(listFormat)
    ProperMQL = fixJSON(MQL, jsonTries)
    return ProperMQL


def fixJSON(text, tries: int = 3, maxTemperature: float = 1):
    jsonText = text
    jsonAttempt = None

    try:
        jsonAttempt = json.loads(jsonText)
        print("JSON is valid, does not need fixing")
        return jsonAttempt
    except:
        print("Your json is not valid, attempting to fix it.")

    for i in range(tries):
        temperature = i*(maxTemperature/(tries-1))
        jsonText = AskAI(prompt=fixJSONPrompt, text=jsonText,
                         temperature=temperature)
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


def pretty_print_conversation(messages):
    role_to_color = {
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


# def GetDescription(level: str, clinicalTrial: str) -> str:
#     descriptionTemplate = "You will be given a json containing information about a clinical trial. you will provide a one paragraph summary that a {level} can understand. Do not change any of the facts, you must not alter any of the meanings. the clinical trial json is as follows: {clinicalTrial}"
#     descriptionPrompt = PromptTemplate.from_template(descriptionTemplate)
#     descriptionChain = LLMChain(llm=llm, prompt=descriptionPrompt)

    # return descriptionChain.run(level, clinicalTrial)


# # possible problem is merging something like standard ages [adult] and minimum age : 18. this is different data types for the value. can attack with another llm call but wait to see if have any other ideas
# def MergeVariations(listToMerge: list, listOfAllVariations: list):
#     mergeVariationsTemplate = """You are a merger. You will be given two lists of properties. Your job is to identify if any property from one list can be classified as the same as a property on the other list. They may differ by wording, capitalization or synonyms but must mean the same thing. For example the properties "ECOG Status" and "ecog medical status" mean the same thing and must be merged. You will return a csv with 3 columns and as many rows as needed. each row will contain a pair of properties that can be merged and what they will be merged to. Do not merge them if they do not mean the same thing or have nothing to do with each other. THEY MUST BE ONLY BE MERGED IF THEY MEAN THE SAME THING, DO NOT MERGE TWO PROPERTIES WHICH DON'T CORRELATE.
#     An example row could be: "able to provide informed consent", "capable of providing informed consent", "can provide consent".

#     each item in the list will seperated by a pipe character |. For example: item1| item2| item3
#     your output will also seperate the items with a pipe character |. it MUST be in the following format: Exact property from list 1| EXACT property from list 2| merged property\n

#     DO NOT MERGE TWO THINGS THAT ARE EXACTLY THE SAME, ONLY IF THEY DIFFER BY WORDING, CAPITALIZATION OR SYNONYMS BUT MEAN THE SAME THING.
#     if there is nothing to merge then ouptut "nothing to merge" DO NOT OUTPUT ANYTHING ELSE.

#     List 1: {list1}

#     List 2: {list2}

#     | seperate values Output:

#     """

#     mergeVariationsPrompt = PromptTemplate(
#         input_variables=["list1", "list2"], template=mergeVariationsTemplate)
#     textSeperatorChain = LLMChain(
#         llm=llm, prompt=mergeVariationsPrompt, verbose=True)

#     output = textSeperatorChain.__call__(
#         {"list1": listToMerge, "list2": listOfAllVariations})

#     # # Convert the CSV string to a file-like object
#     # csv_file = io.StringIO(output)

#     # # Parse the CSV file into a 2-dimensional list
#     # csv_reader = csv.reader(csv_file)
#     # csv_list = [row for row in csv_reader]

#     return output
