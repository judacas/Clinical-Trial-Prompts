import glob
import json
import os
import shutil

import newRawDataController as trialGetter
from prompt_toolkit import prompt
from prompt_toolkit.completion import WordCompleter
from trial import Trial
from errorManager import logError

TRIALS_FOLDER = os.path.join(os.path.dirname(os.getcwd()), "Trials")


def process_trials():
    hasFetched = getValidInput("Have you fetched the trials?", valid_answers=["Yes", "No"], printOptions=True, verbose=True, keepTrying=True)
    if hasFetched == "No":
        folder = getRawTrials()
    else:
        categories = os.listdir(TRIALS_FOLDER)
        category = str(getValidInput(question="Enter the category the files are in", valid_answers=categories, printOptions=True, keepTrying=True, verbose=True))
        category_path = os.path.join(TRIALS_FOLDER, category)

        subFolders = os.listdir(category_path)
        subfolder = str(getValidInput(question="Enter the name of the folder the files are in",valid_answers=subFolders,printOptions=True,keepTrying=True,verbose=True))
        folder = os.path.join(category_path, subfolder)

    # Get a list of all JSON files in the folder
    print("Processing trials in folder: ", folder)
    json_files = glob.glob(os.path.join(folder, "*.json"))
    print("Found", len(json_files), "files")

    for json_file in json_files:
        print(os.path.basename(json_file))
        with open(json_file) as file:
            rawTrial = json.load(file)
            trial = Trial(rawJSON=rawTrial,verbose=True,)
            try:
                trial.finishTranslation(verbose=True)
                trial_json = trial.toJSON()
                trialGetter.saveTrialToFile(trial_json, folder, suffix="_Processed")
            except Exception as e:
                logError(e=e, during=f"processing trial{trial.nctId}")


# TODO: Re implement talking to a trial
def talk_to_trial():
    print("No longer implemented for now")


def getRawTrials():
    categories = os.listdir(TRIALS_FOLDER)
    while True:
        category = str(getValidInput(question="Enter the category you want to save your trials in", valid_answers=categories, keepTrying=False, printOptions=True, verbose=False))
        if category not in categories:
            if getValidInput("This a new category, did you want to make it or try again?", valid_answers=["Make it", "Try again"], printOptions=True, keepTrying=True) == "Try again":
                continue
            os.makedirs(os.path.join(TRIALS_FOLDER, category))
            break
        else:
            break
    while True:
        folder = str(getValidInput(question="Enter the name of the folder you want to save the trials in, you may overWrite any of the following or make a new folder", valid_answers=os.listdir(os.path.join(TRIALS_FOLDER, category)), keepTrying=False, printOptions=True,verbose=False))
        if folder in os.listdir(os.path.join(TRIALS_FOLDER, category)):
            if getValidInput(question="This folder already exists, did you want to overwrite it?", valid_answers=["Yes", "No"], keepTrying=True, printOptions=True) == "Yes":
                shutil.rmtree(os.path.join(TRIALS_FOLDER, category, folder))
                os.makedirs(os.path.join(TRIALS_FOLDER, category, folder))
                break
            else:
                continue
        else:
            print(f"Making folder {folder} in {category}")
            os.makedirs(os.path.join(TRIALS_FOLDER, category, folder))
            
            break
    folder = os.path.join(TRIALS_FOLDER, category, folder)
    num = int(getValidInput("Enter the number of trials to fetch: ", valid_type=int)) # type: ignore
    isChia = getValidInput("Are you fetching Chia trials?", valid_answers=["Yes", "No"], printOptions=True, keepTrying=True, verbose=True)

    if isChia == "Yes":
        startIndex = int(getValidInput("Enter the starting index: ", valid_type=int)) # type: ignore
        trialGetter.saveCHIATrials(n=num, start_index=startIndex, folder=folder)
    else:
        # ! NOT PROPER FOLDER STRUCTURE YET
        # TODO fix Random trials saver and getter to switch to one file per trial
        trialGetter.saveRandomTrialsToFile(n=num)

    return folder

def exit_program():
    print("Goodbye!")
    exit()


def list_completer(text, state, valid_inputs):
    options = [str(x) for x in valid_inputs if str(x).startswith(text)]
    return options[state % len(options)]

# ! beware! if you set keepTrying to False, the function will return the normal user input should the user not provide a valid input, you must validate outside of the function by seeing if it is in valid_answers
# this was done so it would do the proper case if that's what they messed up on and still letting you see what they natively chose in case you need to do something with it
def getValidInput(question: str, valid_type: type = None, valid_answers: list = None, printOptions=False, keepTrying=True, verbose = True):  # type: ignore
    # this is just xoring them so that only one of them can be given
    if valid_type is None != valid_answers is None:
        logError(customText="Come on now you can't be causing an error when trying to get valid input, include either the type or the valid answers please", during="validation of input", e = "Verschlimmbesserung")
        raise ValueError("You must provide exactly one of valid_type or valid_answers")

    while True:
        if valid_answers is not None:
            completer = WordCompleter(valid_answers, ignore_case=True)
            question += f" {valid_answers} - " if printOptions else " - "
            answer = prompt(question, completer=completer)
            if answer.lower() in (valid_answer.lower() for valid_answer in valid_answers):
                return answer
            if verbose:
                print("Input was not one of the valid options.")
            if not keepTrying:
                return answer
            else:
                print("Please try again.")
                continue
        else:
            try:
                # Try to convert the input to the valid type
                answer = valid_type(prompt(question))
                return answer
            except ValueError:
                print(
                    f"Invalid input. Please enter a value of type {valid_type.__name__}."
                )
                if not keepTrying:
                    return answer


def main():
    menu_options = [
        {"label": "Get raw trials", "function": getRawTrials},
        {"label": "Process trials", "function": process_trials},
        {"label": "Talk to trial", "function": talk_to_trial},
        {"label": "Exit", "function": exit_program},
    ]

    label_to_function = {
        option["label"].lower(): option["function"] for option in menu_options
    }

    # Create a list of valid answers: the numbers and the labels
    valid_answers = [str(i + 1) for i in range(len(menu_options))] + [
        option["label"].lower() for option in menu_options
    ]

    while True:
        while True:
            for i, option in enumerate(menu_options, start=1):
                print(f"{i}. {option['label']}")
            choice = getValidInput("Choose an option", valid_answers=valid_answers, keepTrying=False, printOptions=False)
            if choice in valid_answers:
                break
        choice = str(choice)
        if choice.isdigit(): 
            menu_options[int(choice) - 1]["function"]()
        else:
            label_to_function[choice]()


if __name__ == "__main__":
    main()
