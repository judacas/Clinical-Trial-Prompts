from typing import Optional, Any
from dotenv import load_dotenv, find_dotenv
import os
import openai
import json

from sqlalchemy import null
from prompts import booleanPrompt, MQLPrompt, fixJSONPrompt, BackgroundPrompt
from termcolor import colored

# from dotenv import load_dotenv, find_dotenv
# load_dotenv(find_dotenv())

GPTmodel = "gpt-3.5-turbo"

load_dotenv(find_dotenv())
openai.api_key = os.getenv("OPENAI_API_KEY")


def AskAI(text: str, prompt: Optional[BackgroundPrompt] = None, model: str = GPTmodel, temperature: float = 0, maxAttempts: int = 3, verbose: bool = True) -> Optional[str]:
    print("ASKING AI")
    if prompt is not None:
        allMessages = prompt.messages
        allMessages.append(formatTextAsMessage(text, role="user"))
    else:
        allMessages = [formatTextAsMessage(text, role="user")]

    i = 0
    response = None
    for i in range(3):
        try:
            response = openai.ChatCompletion.create(  # ignore
                model=model, messages=allMessages, temperature=temperature)  # ignore
            break
        except Exception as e:
            print(f"Attempt {i+1} was a failer\n Error: {e}. Retrying...")
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


def extractResponse(response) -> str:
    return response["choices"][0]["message"]["content"]


def formatTextAsMessage(text: str, role: str = "user", name: Optional[str] = None) -> "dict[str,str]":
    message = {
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


# print("getting response")
# response = AskAI(text="hello")
# print(response)
TranslateTextToMQL("""eligibilityCriteria": "Inclusion Criteria:\n\n* Understand and voluntarily sign an informed consent document prior to conducting any study related assessments or procedures.\n* Histologically proven invasive adenocarcinoma of breast.\n* Must have marker clip indicating location of target tumor in breast.\n* Unifocal tumor less than or equal to 2 cm based on contrast-enhanced prone-breast MRI.\n* Must be clinically and radiographically node negative (N0) to participate on this protocol. Clinically suspicious regional nodes by imaging or physical exam require biopsy evaluation to exclude disease involvement.\n* Appropriate candidate for breast-conserving surgery based on multi-disciplinary assessment.\n* Females age ≥ 50 years.\n* Able to tolerate prone body positioning during radiation therapy.\n* No prior ipsilateral-breast or thoracic radiotherapy.\n* As defined on MRI, target lesion must be at least 10 mm distance from skin (defined as volume encompassing first 3 mm from breast surface).\n* Must be estrogen receptor (ER) positive.\n* Must be negative for Her-2 amplification. (Either 1+ on semi-quantitative evaluation of immunostain or negative by fluorescent in-situ hybridization).\n* No implanted hardware or other material that would prohibit appropriate treatment planning or treatment delivery in the investigator's opinion.\n* No history of an invasive malignancy (other than this breast cancer, or non-metastatic basal or squamous skin cancers) in the last 5 years.\n* Must not have received nor be planned for neoadjuvant chemotherapy prior to SABR or surgery.\n* ECOG performance status less than 2.\n* Females of childbearing potential must have a negative urine pregnancy test prior to simulation and within seven days of SABR start.\n\nExclusion Criteria:\n\n* Have invasive lobular carcinoma.\n* Have a Tumor \\> 2 cm as measured on prone contrast-enhanced breast MRI.\n* Have presence of histologically proven lymph node disease.\n* Are not a candidate for breast conserving surgery.\n* Have had prior ipsilateral-breast or thoracic radiotherapy.\n* History of scleroderma or lupus erythematosus with either cutaneous manifestation or requiring active treatment.\n* An MRI defined target tumor that is within 10 mm of skin (defined as volume encompassing first 3 mm from skin surface).\n* Have amplification of Her-2 (Either 3+ by semi-quantitative immunostain or positive by Fluorescent in-situ hybridization (FISH)).\n* Have implanted hardware or other material that would prohibit appropriate treatment planning or treatment delivery in the investigator's opinion.\n* History of an invasive malignancy (other than this breast cancer, or non-metastatic basal or squamous skin cancers) in the last 5 years.\n* Have received or plan to receive neoadjuvant chemotherapy either before radiotherapy or before surgery.\n* A known carrier of BRCA1 or BRCA2 gene mutation.\n* Pregnant or unwilling to undergo pregnancy screening.",
#     "healthyVolunteers": false,
#     "sex": "FEMALE",
#     "minimumAge": "50 Years",
#     "stdAges": [
#       "ADULT",
#       "OLDER_ADULT"
#     ]""")

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
