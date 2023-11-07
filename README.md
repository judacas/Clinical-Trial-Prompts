# NOTE: This is a work in progress and is not in a working state.

the code is currently getting revamped to be much more effective and accurate. To see the last working state with a database go to https://github.com/judacas/Clinical-Trial-Prompts/tree/d85faabad3c8168bf0336fd97ce6747af829abfa

# Chat GPT Prompts Workspace

This workspace aims to contribute to the matching of patients with their corresponding clinical trials . It uses ChatGPT to change clinical trial eligibility requirements, which comes in a free text format, into a formatted boolean algebra structure. ChatGPT then takes this structured data and converts it to Mongo query language. which can then be queried using MongoDB. It will then utilize a chatbot UI to gather information from the user untill it has all the information it needs to match a user with their corresponding clinical trials.

## Details

The code uses OpenAI’s ChatGPT (gpt-3.5-turbo-0613) (gpt-3.5-turbo-16k-0613 for large descriptions) via the OpenAI API with Python (v3.11.4) bindings with a temperature of 0 for all prompts except for fixing JSONS; for which the temperature value increased each try. The code uses the ClinicalTrials.gov REST API 2.0.0-draft to fetch clinical trials. The code has been tested using ten interventional cancer clinical trials. Responses were evaluated for correctness and prompts were modified in an iterative development process. Prompts were decomposed into more specific subtasks and examples were manually derived. The prompts can be found in prompts.py

### Pre-requisites

Before you run the program, you must make your own .env file and add your openAI API key. The file that should be run is the main.py file.

run `pip install -r requirements.txt` to install all the dependencies.
