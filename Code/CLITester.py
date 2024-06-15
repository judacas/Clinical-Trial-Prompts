import argparse
import os
import shutil
import glob
import json

import newRawDataController as trialGetter
from trial import Trial
from errorManager import logError

TRIALS_FOLDER = os.path.join(os.path.dirname(os.getcwd()), "Trials")

def process_trials(folder):
    folder = os.path.join(TRIALS_FOLDER, folder)
    json_files = glob.glob(os.path.join(folder, "*.json"))

    for json_file in json_files:
        with open(json_file) as file:
            rawTrial = json.load(file)
            trial = Trial(rawJSON=rawTrial,verbose=False,)
            try:
                trial.finishTranslation(verbose=False)
                trial_json = trial.toJSON()
                trialGetter.saveTrialToFile(trial_json, folder, suffix="_Processed")
            except Exception as e:
                logError(e=e, during=f"processing trial{trial.nctId}")

def get_raw_trials(num, start_index, category, folder):
    if category not in os.listdir(TRIALS_FOLDER):
        os.makedirs(os.path.join(TRIALS_FOLDER, category))

    if folder in os.listdir(os.path.join(TRIALS_FOLDER, category)):
        shutil.rmtree(os.path.join(TRIALS_FOLDER, category, folder))
    os.makedirs(os.path.join(TRIALS_FOLDER, category, folder))

    folder = os.path.join(TRIALS_FOLDER, category, folder)
    trialGetter.saveCHIATrials(n=num, start_index=start_index, folder=folder)

def main_cli():
    parser = argparse.ArgumentParser(description='Process some trials.')
    subparsers = parser.add_subparsers(dest='command')

    get_raw_trials_parser = subparsers.add_parser('get_raw_trials')
    get_raw_trials_parser.add_argument('--num', type=int, required=True)
    get_raw_trials_parser.add_argument('--start_index', type=int, required=True)
    get_raw_trials_parser.add_argument('--category', type=str, required=True)
    get_raw_trials_parser.add_argument('--folder', type=str, required=True)

    process_trials_parser = subparsers.add_parser('process_trials')
    process_trials_parser.add_argument('--folder', type=str, required=True)

    args = parser.parse_args()

    if args.command == 'get_raw_trials':
        get_raw_trials(num=args.num, start_index=args.start_index, category=args.category, folder=args.folder)
    elif args.command == 'process_trials':
        process_trials(folder=args.folder)
    else:
        logError(customText=f"Invalid command: {args.command}", during="parsing command line arguments")

if __name__ == "__main__":
    main_cli()