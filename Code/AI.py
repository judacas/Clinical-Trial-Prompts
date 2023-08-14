import io
import csv
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
    textSeperatorTemplate = """Your role is to separate the given large strings of text into distinct requirements for participation in a Clinical trial. Each requirement should be self-contained and specific. If the text is already naturally separated with new lines, do not join the lines together, but you may further divide the text if necessary. If a requirement is asking for certain results for a test in a certain time frame, that is two different requirements, last taken and results needed. If there are indications like 'Inclusion Criteria:' or 'Exclusion Criteria:', use them as dividers for different sections. Ensure that each requirement is comprehensible on its own; if a requirement depends on another to make sense, they should be merged. Separate each requirement with a new line and no additional characters. Additionally you MUST transform each requirement into the format [property: value]. This is not summary: description, but it is a concise property and a concise value

examples{

    Original: 'Must be older than 18 years old.'
    Altered: 'Age: greater than 18'

    Original: 'Electrocardiogram without evidence of acute cardiac ischemia \u00e2\u2030\u00a4 21 days prior to randomization'
    Altered: 'Minimum number of days Electrocardiogram was taken prior to randomization: 21
Latest Electrocardiogram has evidence of acute cardiac ischemia : false'"
}
    
Text to be seperated: 
    {text}
    
Seperate Sections:
    """
    textSeperatorPrompt = PromptTemplate(
        input_variables=["text"], template=textSeperatorTemplate)
    textSeperatorChain = LLMChain(
        llm=llm, prompt=textSeperatorPrompt, verbose=True)

    textHomogenizerTemplate = """Your role is to homogenize text. You will have a text and a list. your job is to modify the text to use the same modal expressions and terms as the list. You will replace words in the text with with their corresponding modal expressions and  terms in the list IF THEY HAVE THE SAME MEANING AND IT WON'T CHANGE THE MEANING OF THE TEXT. Do not change a word if it will change the meaning of the text. You will return the modified text. You will not change the text in any other way other than replacing modal expressions and terms with their corresponding pairs from the list. You will ONLY replace modal expressions and terms in the text and add Any important modal expressions and terms that were not altered to the list. DO NOT include any numbers in the list. The items in the list will be seperated via commas. Never return the list as "N/A", instead make the list based on the text. In either case, You will return two things: the modified text, and the updated list of words/phrases"""

    listToMQLTemplate = """You are an encoder/translater. your only job is to encode a list of requirements into a mongo db query written in Mongo DB Query Language (MQL for short) which follows the json formatting rules. MQL uses the operators ["$and", "$or", "$not"] which can be nested an infinite amount of times to represent matches. it also uses equality operators such as \"gte\",\"lt\" and many more. Additionally when seeing if a condition has certain values it can use in array \"\"$in\": [\"Value1\", \"Value2\"]\"
    You must not use the \"$exists\" operator. Instead, have the condition be a boolean. 
    for example say \"has prior systematic Therapy\": true
    However, you must avoid using true or falses if you can use a category instead. For example 
    DO NOT say \"has lung cancer\": true. 
    INSTEAD YOU SHOULD SAY \"cancer type\": \"Lung Cancer\"
    Requirements must be in the format of Mongo DB Query language. Mongo DB query language is VERY important, IT MUST BE MONGO DB QUERY LANGUAGE (MQL). Only use the equality operators for numbers. All brackets my be closed and all properties must be surrounded in double quotes.
    If it is a yes or no question you are to put true or false as the value.
    If there is a number somewhere then the number is to go in the value not the property. for example say \"age\": gt: 18 INSTEAD OF THE WRONG SAYING \"age greater than 18\": true. Numbers should be in the value not the property and with a gt, lt, gte, lte, or eq operator.
    There must only be one condition at a time for each segment. Conditions must be wrapped in quotation marks and specific, for example don't say \"stage\", instead say \"Cancer Stage\". No amount of text is too complicated or long to put into MongoDB query language, it will always be possible. DO NOT, UNDER ANY CIRCUMSTANCES MAKE ASSUMPTIONS. Only translate what is in the text and nothing else. Whenever possible, use numbers. For example, don't describe the age in words such as child, adult, or senior adult. Instead, use numbers and equalities lt 18, gt18 and lt 65 and gt 65
    From now on, you will only be given a list of requirements which must all be met. You will respond with only the MongoDB Query language translation.
    After making the MQL translation, you will verify to make sure it is valid Mongo query language. It is CRITICAL that the translation be proper MQL.
    List of Requirements:"
    {ListOfRequirements}
    "
    MQL Translation:
    """
    listToMQLPrompt = PromptTemplate(
        input_variables=["ListOfRequirements"], template=listToMQLTemplate)
    listToMQLChain = LLMChain(llm=llm, prompt=listToMQLPrompt, verbose=True)

    textToMQLChain = SimpleSequentialChain(
        chains=[textSeperatorChain, listToMQLChain], verbose=True)

    return textToMQLChain.run(TextEligibility)


# possible parsing prompt
"""Your job is to group pieces of text together in a more legible format for a computer

Role: You are Experienced in oncology, cancer, and Boolean algebra

Context: You will be given a piece of text that contains criteria to determine whether a subject is eligible to participate in a cancer research clinical trial. This text may have a section called inclusion criteria and another called exclusion criteria, this is important for your task. if it does not specify, then by default it is inclusion criteria

Task: You have to process the input text and structure/group/format it according to boolean algebra rules. All listed "Inclusion Criteria" must be met. This means that every single one of those criteria must operate under an "AND" condition. 
If there are three Inclusion requirements (A, B, C ) then the criteria would be represented as: 
"$and" : [
    {A},
    {B},
    {C}
]
If any of the "Exclusion Criteria" are met, the subject is to be deemed ineligible. This Requires an "OR" operation between each of these criteria, and a "NOT" operation that surrounds the entire set. If there are three Exclusion Requirements (A,B,C) then the criteria would be represented as: 
"$not" : {
    "$or" :[
        {A},
        {B},
        {C},
    ]
}

The Inclusion and exclusion criteria then get ANDed together.

It is CRITICAL that you close every parenthesis that you open. There may also be nested operators within each other, with no limit as to how many levels they are nested

Your output must be in the same format as the examples above. ANDs and ORs use []. NOTs use {}. You are to only output this formatted boolean algebra criteria.

Below is an example of some input and what you ought to output

example text:
Inclusion Criteria:\n\n• Patients with pathologically confirmed pancreatic cancer referred for image guided radiation therapy (IGRT)\n\nExclusion Criteria:\n\n* Age \\<18\n* Inability to consent\n* Known coagulopathy/thrombocytopenia (INR \\>1.5, platelets \\<75)\n* Patients on antiplatelet/anticoagulant medication that cannot safely be discontinued 5-7 days prior to the procedure\n* Gold allergy\n* Current infection\n* EUS evidence of vessel interfering with path of fiducial marker\n* Pregnancy

example output:
"$and": [
    {
        "$and": [
            {
                "pathologically confirmed pancreatic cancer"
            },
            {
                "referred for image guided radiation therapy (IGRT)"
            }
        ]
    },
    {
        "$not": {
            "$or": [
                {
                    "less than 18 years old"
                },
                {
                    "Unable to consent"
                },
                {
                    "has Known coagulopathy/thrombocytopenia"
                },
                {
                    "$and":[
                        {
                            "is on antiplatelet/anticoagulant medication"
                        },
                        {
                            "cannot get off antiplatelet/anticoagulant medication 5-7 days prior to procedure"
                        }
                    ]
                },
                {
                    "has gold allergy"
                },
                {
                    "has current infection"
                },
                {
                    "has EUS evidence of vessel interfering with path of fiducial marker"
                },
                {
                    "is pregnant"
                }
                
            ]
        }
    }
]
"""
