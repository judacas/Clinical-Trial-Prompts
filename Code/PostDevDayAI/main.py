import json

from Patient import Patient
from trial import Trial


def main():
    reprocessTrials = input("Reprocess trials? (y/n): ")
    if reprocessTrials.lower() == "n":
        # Load trials from JSON file
        with open("serializedTrials.json") as json_file:
            trials_json = json.load(json_file)
            trials = [Trial(serializedJSON=trial) for trial in trials_json["trials"]]
    else:
        with open("trials.json") as file:
            rawTrials = json.load(file)["studies"]

            trials = [Trial(rawTrial, verbose=True) for rawTrial in rawTrials]
            for trial in trials:
                trial.finishTranslation(verbose=True)
    # Convert trials to JSON serializable format
    trials_json = [trial.toJSON() for trial in trials]

    # Write trials to a JSON file
    with open("serializedTrials.json", "w") as outfile:
        json.dump({"trials": trials_json}, outfile, indent=4)
    patient = Patient("testPatient")
    patient.acquireInformation(
        {"are you over 18?": "", "do you have cancer?": "", "is your ecog score 0?": ""}
    )
    # patient.acquireInformation(trials[0].rawJSON["eligibilityModule"])


if __name__ == "__main__":
    main()
