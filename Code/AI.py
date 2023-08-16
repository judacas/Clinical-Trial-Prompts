import io
import csv
from langchain.chains import LLMChain
from langchain.chains import SimpleSequentialChain
from langchain.llms import OpenAI
from langchain import PromptTemplate
from prompts import fixJSONTemplate, booleanParserTemplate, listToMQLTemplate

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
    # fixJSONPrompt = PromptTemplate.from_template(fixJSONTemplate)
    updatedTemplate = fixJSONTemplate+jsonText + "\n\nOutput:\n"

    print(updatedTemplate)

    result = llm(updatedTemplate)

    print(result)

    return result


# possible problem is merging something like standard ages [adult] and minimum age : 18. this is different data types for the value. can attack with another llm call but wait to see if have any other ideas
def MergeVariations(listToMerge: list, listOfAllVariations: list):
    mergeVariationsTemplate = """You are a merger. You will be given two lists of properties. Your job is to identify if any property from one list can be classified as the same as a property on the other list. They may differ by wording, capitalization or synonyms but must mean the same thing. For example the properties "ECOG Status" and "ecog medical status" mean the same thing and must be merged. You will return a csv with 3 columns and as many rows as needed. each row will contain a pair of properties that can be merged and what they will be merged to. Do not merge them if they do not mean the same thing or have nothing to do with each other. THEY MUST BE ONLY BE MERGED IF THEY MEAN THE SAME THING, DO NOT MERGE TWO PROPERTIES WHICH DON'T CORRELATE.
    An example row could be: "able to provide informed consent", "capable of providing informed consent", "can provide consent".
    
    each item in the list will seperated by a pipe character |. For example: item1| item2| item3
    your output will also seperate the items with a pipe character |. it MUST be in the following format: Exact property from list 1| EXACT property from list 2| merged property\n
    
    DO NOT MERGE TWO THINGS THAT ARE EXACTLY THE SAME, ONLY IF THEY DIFFER BY WORDING, CAPITALIZATION OR SYNONYMS BUT MEAN THE SAME THING.
    if there is nothing to merge then ouptut "nothing to merge" DO NOT OUTPUT ANYTHING ELSE.
    
    List 1: {list1}
    
    List 2: {list2}
    
    | seperate values Output:
    
    """

    mergeVariationsPrompt = PromptTemplate(
        input_variables=["list1", "list2"], template=mergeVariationsTemplate)
    textSeperatorChain = LLMChain(
        llm=llm, prompt=mergeVariationsPrompt, verbose=True)

    output = textSeperatorChain.__call__(
        {"list1": listToMerge, "list2": listOfAllVariations})

    # # Convert the CSV string to a file-like object
    # csv_file = io.StringIO(output)

    # # Parse the CSV file into a 2-dimensional list
    # csv_reader = csv.reader(csv_file)
    # csv_list = [row for row in csv_reader]

    return output


def TranslateTextToMQL(TextEligibility):
    updatedTemplate = booleanParserTemplate+TextEligibility + "\n\nOutput:\n"

    print(updatedTemplate)

    listFormat = llm(updatedTemplate)

    print(listFormat)

    updatedTemplate = listToMQLTemplate+listFormat + "\n\nOutput:\n"

    print(updatedTemplate)

    result = llm(updatedTemplate)

    print(result)

    return result
    # listToMQLPrompt = PromptTemplate(template=updatedTemplate)
    # listToMQLChain = LLMChain(llm=llm, prompt=listToMQLPrompt, verbose=True)

    # # textToMQLChain = SimpleSequentialChain(
    # #     chains=[textSeperatorChain, listToMQLChain], verbose=True)

    # return listToMQLChain.run()
