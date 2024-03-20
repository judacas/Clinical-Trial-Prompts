## NOTE: This is a work in progress and is not in a working state.

the code is currently getting revamped to be much more effective and accurate. To see the previous version which used MongoDB instead of boolean expressions go to https://github.com/judacas/Clinical-Trial-Prompts/tree/d85faabad3c8168bf0336fd97ce6747af829abfa

## Large Language Models for Translating Clinical Trial Eligibility Criteria into Structured Data

This workspace aims to contribute to the matching of patients with their corresponding clinical trials . It uses ChatGPT to change clinical trial eligibility requirements, which comes in a free text format, into a formatted boolean algebra structure. It will then utilize a chatbot UI to gather information from the user untill it has all the information it needs to match a user with their corresponding clinical trials.

## Details

OpenAI’s GPT (gpt-4-turbo) with Python (v3.11.4) bindings were used to convert ClinicalTrials.gov JSON criteria. Ten (10) interventional clinica trials were chosen for training. Responses were evaluated for correctness, and prompts were modified in an iterative development process. Prompts were decomposed into more specific subtasks. The output was MQL (Mongo Query Language) then updated to Boolean algebra expression serialized as a JSON. The first prompt takes in free form eligibility criteria and outputs a Boolean algebra expression serialized as a JSON. The second prompt then takes that JSON and asks the user until they acquire the information
necessary to evaluate the Boolean expression


## pre requisites
currently the code can not be run out of the box as it does not make an openai assistant from the prompts in this repo. It instead uses assistants already made on our personal openai account for which the id can not be shared.

### work around
install all neccesary requirements by running pip install -r requirements.txt.
you must then make assistants using the openai api and copy the prompts from the txt files into the system prompts. You must also copy the function call text into the Information Gathering tools. Then you must fill out the IDs of each assistant and api keys from your opernai account in a .env file stored in Code\.env
The keys needed are:
OPENAI_API_KEY=""
OPENAI_ORGANIZATION_ID=""
CriteriaBooleanTranslatorID=""
InformationGathererID=""
Fill in the strings with your IDs/Keys
Warning, this will cost money as it is using your personal openaiAPI keys