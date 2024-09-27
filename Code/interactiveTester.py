import json
import os
import shutil
import sys
from typing import Iterable

from loguru import logger
import rich

import newRawDataController as trialGetter
from prompt_toolkit import prompt
from prompt_toolkit.completion import WordCompleter
import analyzer
from newTrial import Trial, RawTrialData
TRIALS_FOLDER = os.path.join(os.path.dirname(os.getcwd()), "Trials")
CHIA_FOLDER = os.path.join(os.path.dirname(os.getcwd()), "CHIA")


def old_process_trials():
    hasFetched = getValidInput("Have you fetched the trials?", validAnswers=["Yes", "No"], printOptions=True, verbose=True, keepTrying=True)
    folder = getRawTrials() if hasFetched == "No" else getTrialFolder()
    # Get a list of all JSON files in the folder
    analyzer.processTrialsInFolder(folder)

# TODO: could use the getTrialFolder but it has some special cases that need to be handled
# Definitely should be refactored in the future, its quite messy and in reality could be as simple as process_trials
def getRawTrials():
    categories = os.listdir(TRIALS_FOLDER)
    while True:
        category = str(getValidInput(question="Enter the category you want to save your trials in", validAnswers=categories, keepTrying=False, printOptions=True, verbose=False))
        if category not in categories:
            if getValidInput("This a new category, did you want to make it or try again?", validAnswers=["Make it", "Try again"], printOptions=True, keepTrying=True) == "Try again":
                continue
            os.makedirs(os.path.join(TRIALS_FOLDER, category))
        break
    while True:
        folder = str(getValidInput(question="Enter the name of the folder you want to save the trials in, you may overWrite any of the following or make a new folder", validAnswers=os.listdir(os.path.join(TRIALS_FOLDER, category)), keepTrying=False, printOptions=True,verbose=False))
        if folder in os.listdir(os.path.join(TRIALS_FOLDER, category)):
            if (getValidInput(question="This folder already exists, did you want to overwrite it?",validAnswers=["Yes", "No"],keepTrying=True,printOptions=True)== "No"):
                continue
            shutil.rmtree(os.path.join(TRIALS_FOLDER, category, folder))
        else:
            logger.trace(f"Making folder {folder} in {category}")
        os.makedirs(os.path.join(TRIALS_FOLDER, category, folder))
        break
    folder = os.path.join(TRIALS_FOLDER, category, folder)
    num = int(getValidInput("Enter the number of trials to fetch: ", validType=int)) # type: ignore
    isChia = getValidInput("Are you fetching Chia trials?", validAnswers=["Yes", "No"], printOptions=True, keepTrying=True, verbose=True)

    if isChia == "Yes":
        startIndex = int(getValidInput("Enter the starting index: ", validType=int)) # type: ignore
        trialGetter.saveCHIATrials(n=num, start_index=startIndex, folder=folder, suffix="Raw")
    else:
        # ! NOT PROPER FOLDER STRUCTURE YET
        # TODO fix Random trials saver and getter to switch to one file per trial
        logger.critical("Random trials are not yet implemented")
        trialGetter.saveRandomTrialsToFile(n=num)

    return folder

def exit_program():
    print("Goodbye!")
    exit()


def list_completer(text, state, valid_inputs):
    options = [str(x) for x in valid_inputs if str(x).startswith(text)]
    return options[state % len(options)]

def getValidInput(question: str, validType: type = None, validAnswers: Iterable = None, printOptions=False, keepTrying=True, verbose=True):  # type: ignore
    if (validType is None) == (validAnswers is None):
        logger.error("You must provide exactly one of valid_type or valid_answers")
        raise ValueError("You must provide exactly one of valid_type or valid_answers")

    def handleValidAnswers() -> str:
        completer = WordCompleter(list(validAnswers), ignore_case=True)
        question_with_options = f"{question} {validAnswers} - " if printOptions else f"{question} - "
        while True:
            answer = prompt(question_with_options, completer=completer)
            if answer.lower() in (valid_answer.lower() for valid_answer in validAnswers):
                return answer
            if verbose:
                print("Input was not one of the valid options.")
            if not keepTrying:
                return answer
            print("Please try again.")

    def handleValidType():
        while True:
            try:
                return validType(answer := prompt(question))
            except ValueError:
                print(f"Invalid input. Please enter a value of type {validType.__name__}.")
                if not keepTrying:
                    return answer # type: ignore

    return handleValidAnswers() if validAnswers is not None else handleValidType()

    
def checkCHIADeprecation():
    comparingFolder = getTrialFolder()
    analyzer.updatedCompareToChia(CHIA_FOLDER, comparingFolder, False)
def compareAgainstCHIA():
    comparingFolder = getTrialFolder()
    analyzer.updatedCompareToChia(CHIA_FOLDER, comparingFolder, True)

def getTrialFolder():
    comparingCategory = getValidInput("Enter the category in which your trials are in", validAnswers=os.listdir(TRIALS_FOLDER), printOptions=True, keepTrying=True, verbose=True)
    comparingCategory = os.path.join(TRIALS_FOLDER, comparingCategory)
    comparingFolder = getValidInput("Enter the folder in which your trials are in", validAnswers=os.listdir(comparingCategory), printOptions=True, keepTrying=True, verbose=True)
    comparingFolder = os.path.join(comparingCategory, comparingFolder)
    return comparingFolder

# TODO Implement fully later once we need to talk with trials with updated structure. For now use the commit Clinical-Trial-Prompts-d5792dd78d94f8a2f0a9ae79159d9c8b14526303 to talk to the old structure
# def talkToTrial():
#     isReady = getValidInput("Hello, Do you have a trial already processed?", validAnswers=["Yes", "No"], printOptions=True, keepTrying=True, verbose=True)
#     if isReady == "No":
#         print("Please process the trial first, You can do that in the main menu")
#         return
#     print("In that case where are the trials you want to see if you're eligible for?")
#     folder = getTrialFolder()
#     isSingular = getValidInput("Are you looking at a specific trial or all of the ones in the folder?", validAnswers=["Specific", "Entire Folder"], printOptions=True, keepTrying=True, verbose=True)
#     # if isSingular == "Specific":
#     #     trial = getValidInput("Enter the ID of the trial you want", validAnswers=analyzer.getNctIdsFromFolder(folder), printOptions=True, keepTrying=True, verbose=True)
#     #     trials = {trial} # type: ignore
#     # else:
#     #     pass
#     #     # trials = analyzer.getNctIdsFromFolder(folder)
#     # myChatBot = ChatBot(folder=folder, trial_ids=trials)
#     # myChatBot.startChat()

def newStructurize():
    logger.trace("Starting structurize")
    ids = analyzer.getNctIdsFromFolder(getRawTrials())
    for id in ids:
        print(id)
        # trial = Trial(raw_data=RawTrialData.fromOnlyNctID(id))
        # rich.print(trial)
        # with open(f"{id}_NewlyStructurized.json", "w") as f:
        #     json.dump(trial.model_dump_json(serialize_as_any=True), f, indent=4)
def notImplemented():
    print("This feature is not implemented yet")
def configure_logger():
    with open("loguru_config.json", "r") as f:
        config = json.load(f)
    
    # Remove the default handler
    logger.remove()
    
    # Add handlers based on the configuration
    for handler in config["handlers"]:
        sink = sys.stdout if handler["sink"] == "stdout" else handler["sink"]
        logger.add(sink, **{key: value for key, value in handler.items() if key != "sink"})
def main():  # sourcery skip: merge-list-append
    configure_logger()
    
    logger.trace("Starting program")
    logger.info("Welcome to the interactive tester!")
    logger.critical("This is a critical message")
    menu_options = [
        {"label": "Get raw trials", "function": getRawTrials},
        {"label": "Deprecated Process trials", "function": old_process_trials},
        {"label": "Test new Structure", "function": newStructurize},
        {"label": "Compare to Chia", "function": compareAgainstCHIA},
        {"label": "Check CHIA's deprecation", "function": checkCHIADeprecation}
    ]
    # done so that Exit is always the last option
    menu_options.append({"label": "Exit", "function": exit_program})

    label_to_function = {
        option["label"].lower(): option["function"] for option in menu_options
    }

    # Create a list of valid answers: the numbers and the labels
    valid_answers = [str(i + 1) for i in range(len(menu_options))] + [
        option["label"].lower() for option in menu_options
    ]

    while True:
        print("\n\nMain Menu\n")
        while True:
            for i, option in enumerate(menu_options, start=1):
                print(f"{i}. {option['label']}")
            choice = getValidInput("Choose an option", validAnswers=valid_answers, keepTrying=False, printOptions=False)
            if choice in valid_answers:
                break
        choice = str(choice)
        print("\n")
        if choice.isdigit(): 
            menu_options[int(choice) - 1]["function"]()
        else:
            label_to_function[choice]()


if __name__ == "__main__":
    main()
