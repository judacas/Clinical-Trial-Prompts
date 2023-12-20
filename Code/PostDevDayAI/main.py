import json
from trial import Trial
def main():
    
    with open('trials.json') as file:
        rawTrials = json.load(file)["studies"]

        trials = [Trial(rawTrial, verbose=True) for rawTrial in rawTrials]
        for trial in trials:
            trial.finishTranslation(verbose=True)
            print(trial)
        # Convert trials to JSON serializable format
        trials_json = [trial.toJSON() for trial in trials]

        # Write trials to a JSON file
        with open('output.json', 'w') as outfile:
            json.dump(trials_json, outfile, indent=4)

if __name__ == '__main__':
    main()