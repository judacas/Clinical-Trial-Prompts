from time import sleep
from typing import Optional, Any
from dotenv import load_dotenv, find_dotenv
import os
import openai
import json

import tiktoken
from prompts import booleanPrompt, MQLPrompt, fixJSONPrompt, BackgroundPrompt
from termcolor import colored

GPTModel = "gpt-3.5-turbo"
models = ["gpt-3.5-turbo", "gpt-3.5-turbo-16k"]
contextLimits: dict[str, int] = {
    "gpt-3.5-turbo": 4095,
    "gpt-3.5-turbo-16k": 16384
}

load_dotenv(find_dotenv())
openai.api_key = os.getenv("OPENAI_API_KEY")


def AskAI(text: str, prompt: Optional[BackgroundPrompt] = None, model: str = GPTModel, temperature: float = 0, maxAttempts: int = 3, verbose: bool = True) -> Optional[str]:
    print("ASKING AI")
    allMessages: list[dict[str, Any]] = []
    if prompt is not None:
        allMessages += prompt.messages
    allMessages.append(formatTextAsMessage(text, role="user"))
    i = 0
    response = None
    tokens = num_tokens_from_messages(allMessages, model)
    print(f"tokens: {tokens}")
    pretty_print_conversation(allMessages)
    if tokens >= contextLimits[model]:
        if verbose:
            print(
                f"Too many tokens ({tokens}) for {model}. Please reduce the number of messages in the prompt.")
            model = models[min(len(models), models.index(model)+1)]
    for i in range(maxAttempts):
        try:
            response = openai.ChatCompletion.create(  # ignore
                model=model, messages=allMessages, temperature=temperature)  # ignore
            break
        except openai.error.RateLimitError as e:  # type: ignore
            print(
                f"TOO MANY REQUESTS. waiting and trying again\n OpenAi says {e}")
            sleep(determineWait(maxTries=maxAttempts, waitTime=60, currentTry=i+1))
            continue
        except Exception as e:
            print(f"OpenAi Error: {e}")
            sleep(determineWait(maxTries=maxAttempts, waitTime=60, currentTry=i+1))
            continue

    if i == maxAttempts-1:
        print(f"Failed to get response from AI after {maxAttempts} attempts.")
        return None

    if response["choices"][0]["finish_reason"] == "length":  # type: ignore
        print("Didn't get to finish, might want to try something shorter")

    assert response
    if verbose:
        # allMessages.append(formatTextAsMessage(
        #     extractResponse(response=response), role="assistant"))
        pretty_print_conversation([formatTextAsMessage(
            extractResponse(response=response), role="assistant")])

    return extractResponse(response)


# this function uses the geometric sum formula to calculate how much to wait between attempts while ensuring that by its last attempt it would have tried to wait the max wait, and then one more time after that waiting a full minute
def determineWait(maxTries, waitTime, currentTry, factor=2) -> int:
    initialWait = (waitTime*(1-factor))/(1-factor**maxTries)
    currentWait = initialWait*factor**(currentTry-1)
    assert currentWait <= waitTime
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


def ConvertTextToBool(text: str, model: str = GPTModel, temperature: float = 0, verbose: bool = True) -> Optional[str]:
    print("converting text to bool")
    return AskAI(prompt=booleanPrompt, text=text, model=model, temperature=temperature, verbose=verbose)


def ConvertBoolToMQL(text: str, model: str = GPTModel, temperature: float = 0, verbose: bool = True) -> Optional[str]:
    print("converting bool to MQL")
    return AskAI(prompt=MQLPrompt, text=text, model=model, temperature=temperature, verbose=verbose)


def TranslateTextToMQL(TextEligibility: str, jsonTries: int = 3):
    criteria = extract_criteria(TextEligibility)
    listFormat: str | None = ConvertTextToBool(TextEligibility)
    if listFormat is None:
        print("Could not convert to list")
        return None, None, None
    MQL: str | None = ConvertBoolToMQL(listFormat)
    if MQL is None:
        print("Could not convert to MQL")
        return listFormat, None, None
    ProperMQL: Any | None = fixJSON(MQL, jsonTries)
    return listFormat, MQL, ProperMQL


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


def extract_criteria(input_string: str) -> dict[str, Optional[str]]:
    criteria: dict[str, Optional[str]] = {
        "inclusionCriteria": None,
        "exclusionCriteria": None,
        "bothCriteria": None
    }
    # Split the string into two parts based on "Exclusion Criteria:"
    parts = input_string.split("Exclusion Criteria:")

    # Extract the inclusion and exclusion criteria, or set them to None if not present
    if len(parts) == 2:
        criteria["inclusionCriteria"] = parts[0].replace(
            "Inclusion Criteria:", "").strip()
        criteria["exclusionCriteria"] = parts[1].strip()
    elif len(parts) == 1:
        if "Inclusion Criteria:" in parts[0]:
            criteria["inclusionCriteria"] = parts[0].replace(
                "Inclusion Criteria:", "").strip()
            criteria["exclusionCriteria"] = None
        else:
            criteria["inclusionCriteria"] = None
            criteria["exclusionCriteria"] = parts[0].strip()
    else:
        criteria["bothCriteria"] = parts[0].strip()

    # Return the results as a dictionary
    return criteria


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


text1 = """Inclusion Criteria:\n\n* Patient must be \\>= 18 years of age\n* Patients must have an Eastern Cooperative Oncology Group (ECOG) performance status: 0, 1, or 2 (However, those patients with a performance state of 3 because they are wheel chair bound due to congenital or traumatic events more than one year before the diagnosis of Merkel cell carcinoma are eligible).\n* Patient must have a histological confirmation of diagnosis of Merkel cell carcinoma (MCC), pathologic stages (American Joint Committee on Cancer \\[AJCC\\] version 8) I-IIIb.\n\n  * Stage I patients with negative sentinel lymph node biopsy are ineligible. Patients who have a positive biopsy or for whom no biopsy was done are eligible.\n  * Patients with distant metastatic disease (stage IV) are ineligible.\n  * The primary tumor must have grossly negative margins. (Microscopically positive margins are allowed).\n  * Cancers of unknown primary that have regional disease only are eligible.\n  * Complete nodal dissection is not required for eligibility.\n* Patients with all macroscopic Merkel cell carcinoma (either identified by physical exam or imaging) have been completely resected by surgery within 16 weeks before randomization.\n* All patients must have disease-free status documented by a complete physical examination and conventional imaging studies within 8 weeks prior to randomization.\n* Patient may not have a history of distant metastatic disease.\n\n  * NOTE: Loco-regional recurrent disease is acceptable, as long as this is not metastatic (prior surgery with or without radiation therapy is acceptable).\n* For patients with initial presentation of Merkel cell carcinoma, patient must have no previous systemic therapy or radiation therapy prior to surgery for Merkel cell carcinoma and cannot have completed adjuvant radiation therapy for Merkel cell carcinoma more than 6 weeks prior to randomization. Patients actively undergoing radiation therapy or having completed adjuvant radiation therapy within 6 weeks of randomization are eligible, as long as resection date is within 16 weeks of randomization. Patients with prior radiation at a non-Radiation Oncology Core (IROC) provider are eligible for the trial. If the patient has not received radiation, and treatment at a Radiation Oncology Core (IROC) provider is not possible, the patient can start and complete radiation prior to randomization, with recommendations to follow radiation protocol guidelines with submission of treatment records.\n* White blood count \\>= 2000/uL (within 4 weeks prior to randomization).\n* Absolute neutrophil count (ANC) \\>= 1000/uL (within 4 weeks prior to randomization).\n* Platelets \\>= 75 x 10\\^3/uL (within 4 weeks prior to randomization).\n* Hemoglobin \\>= 8 g/dL (\\>= 80 g/L; may be transfused) (within 4 weeks prior to randomization).\n* Creatinine =\\< 2.0 x institutional upper limit of normal (ULN) (within 4 weeks prior to randomization).\n* Aspartate aminotransferase (AST) and alanine aminotransferase (ALT) =\\< 2.5 x institutional ULN (within 4 weeks prior to randomization).\n* Total bilirubin =\\< 2.0 x institutional ULN, (except patients with Gilbert's syndrome, who must have a total bilirubin less than 3.0 mg/dL) (within 4 weeks prior to randomization).\n* Patients who are human immunodeficiency virus (HIV)+ with undetectable HIV viral load are eligible provided they meet all other protocol criteria for participation.\n* Patients with hepatitis B virus (HBV) or hepatitis C virus (HCV) infection are eligible provided viral loads are undetectable. Patients on suppressive therapy are eligible.\n\nExclusion Criteria:\n\n* Patient must not be pregnant or breast-feeding due to the unknown effects of the study drug in this setting. All patients of childbearing potential must have a blood test or urine study within 2 weeks prior to randomization to rule out pregnancy. A patient of childbearing potential is anyone, regardless of sexual orientation or whether they have undergone tubal ligation, who meets the following criteria: 1) has achieved menarche at some point, 2) has not undergone a hysterectomy or bilateral oophorectomy; or 3) has not been naturally postmenopausal (amenorrhea following cancer therapy does not rule out childbearing potential) for at least 24 consecutive months (i.e., has had menses at any time in the preceding 24 consecutive months).\n* Patients on Arm A MK-3475 (Pembrolizumab) must not conceive or father children by using accepted and effective method(s) of contraception or by abstaining from sexual intercourse from the time of registration, while on study treatment, and continue for 120 days after the last dose of study treatment. For patients on Arm B only receiving radiation therapy, contraception use should be per institutional standard.\n* Patients must not be on active immunosuppression, have a history of life threatening virus, have had other (beside non-melanoma skin cancers, or recent indolent cancers e.g.: resected low grade prostate cancer) invasive cancer diagnoses in the last two years, or have had immunotherapy of any kind within the last 2 years prior to randomization.\n* Patients must not have a history of (non-infectious) pneumonitis that required steroids or has current pneumonitis.\n* Operative notes from patient's surgical resection must be accessible."""


text2 = "must have cancer"

# TranslateTextToMQL(text2)
