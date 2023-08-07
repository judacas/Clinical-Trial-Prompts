from langchain.chains import LLMChain
from langchain.chains import SimpleSequentialChain
from langchain.llms import OpenAI
from langchain import PromptTemplate

from dotenv import load_dotenv, find_dotenv
load_dotenv(find_dotenv())


llm = OpenAI(model_name="text-davinci-003", temperature=0,
             frequency_penalty=0, presence_penalty=0)  # type: ignore


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
    descriptionChain = LLMChain(llm=llm, prompt=descriptionPrompt)

    return descriptionChain.run(level, clinicalTrial)


def FixJSON(jsonText):
    fixJSONTemplate = "You are a JSON editor. You will be given a JSON with a few errors. You must fix the JSON so that it is valid JSON. You must not change any of the properties or values but you will change syntax and formatting, you must not alter any of the meanings. You must make sure all brackets are closed and all properties are surrounded in double quotes and everything follows the rules of json formatting.\nJSON to edit:\n {jsonToFix}\n\nFixed JSON:\n"
    # fixJSONPrompt = PromptTemplate.from_template(fixJSONTemplate)
    fixJSONPrompt = PromptTemplate(
        input_variables=["jsonToFix"], template=fixJSONTemplate)
    fixJSONChain = LLMChain(llm=llm, prompt=fixJSONPrompt, verbose=True)

    return fixJSONChain.run(jsonText)


def TranslateTextToMQL(TextEligibility):
    textSeperatorTemplate = """Your role is to separate large strings of text into separate sections. The texts within each section must be related to each other. If the text is already naturally sepreated with new lines leave it as is. If it says inclusion or exlcusion criteria, use it to seperate the text. Each section must be able to make sense on its own, if a section depends on another section to make sense then they should be merged. YOU ARE LIMITED IN HOW YOU MAY ALTER THE TEXT, YOU MAY ONLY REMOVE PHRASES (such as \"Step 1:\") which ARE NOT IMPORTANT IN IDENTIFYING WHETHER A PATIENT QUALIFIES OR NOT. YOU WILL NOT ALTER THE TEXT IN ANY OTHER WAY OTHER THAN WHAT WAS LISTED BEFORE AND FORMATING.   You will seperate each section of text with a new line and nothing else, no numeration.
    Text to be seperated: {text}
    Seperate Sections:
    """
    textSeperatorPrompt = PromptTemplate(
        input_variables=["text"], template=textSeperatorTemplate)
    textSeperatorChain = LLMChain(
        llm=llm, prompt=textSeperatorPrompt, verbose=False)

    listToMQLTemplate = """You are an encoder/translater. your only job is to encode a list of requirements into a mongo db query written in Mongo DB Query Language (MQL for short) which follows the json formatting rules. MQL uses the operators ["$and", "$or", "$not"] which can be nested an infinite amount of times to represent matches. it also uses equality operators such as \"gte\",\"lt\" and many more. Additionally when seeing if a condition has certain values it can use in array \"\"$in\": [\"Value1\", \"Value2\"]\"
    You must not use the \"$exists\" operator. Instead, have the condition be a boolean. 
    for example say \"has prior systematic Therapy\": true
    However, you must avoid using true or falses if you can use a category instead. For example 
    DO NOT say \"has lung cancer\": true. 
    INSTEAD YOU SHOULD SAY \"cancer type\": \"Lung Cancer\"
    Requirements must be in the format of Mongo DB Query language. Mongo DB query language is VERY important, IT MUST BE MONGO DB QUERY LANGUAGE (MQL). Only use the equality operators for numbers. All brackets my be closed and all properties must be surrounded in double quotes.
    If it is a yes or no question you are to put true or false as the value.
    There must only be one condition at a time for each segment. Conditions must be wrapped in quotation marks and specific, for example don't say \"stage\", instead say \"Cancer Stage\". No amount of text is too complicated or long to put into MongoDB query language, it will always be possible. DO NOT, UNDER ANY CIRCUMSTANCES MAKE ASSUMPTIONS. Only translate what is in the text and nothing else. Whenever possible, use numbers. For example, don't describe the age in words such as child, adult, or senior adult. Instead, use numbers and equalities lt 18, gt18 and lt 65 and gt 65
    From now on, you will only be given a list of requirements which must all be met. You will respond with only the MongoDB Query language translation.
    After making the MQL translation, you will verify to make sure it is valid Mongo query language. It is CRITICAL that the translation be proper MQL.
    List of Requirements: {ListOfRequirements}
    MQL Translation:
    """
    listToMQLPrompt = PromptTemplate(
        input_variables=["ListOfRequirements"], template=listToMQLTemplate)
    listToMQLChain = LLMChain(llm=llm, prompt=listToMQLPrompt, verbose=False)

    textToMQLChain = SimpleSequentialChain(
        chains=[textSeperatorChain, listToMQLChain], verbose=True)

    return textToMQLChain.run(TextEligibility)
