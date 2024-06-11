import json
from trial import Trial
import newRawDataController as trialGetter

# print(trialGetter.getChiaIDs(10,10))
# trialGetter.saveCHIATrialsToFile(10,10)
# trial = {"studies": [trialGetter.getTrialByNCTID(trialGetter.getChiaIDs(1)[0]), "testTrial.json"]}
# print(trial)
# trialGetter.saveTrialToFile(trial, "testTrial.json")

# trialGetter.saveTrialToFile(trialGetter.processCriteria((trialGetter.getTrialsByID(trialGetter.getChiaIDs(1)))), "testTrial.json")



# trialGetter.saveTrialToFile(trialGetter.getTrialByNCTID(trialGetter.getChiaIDs(1)[0]), "testTrial.json")

trialGetter.saveCHIATrialsToFile(10,10, "CHIAtrials.json")


with open("CHIAtrials.json") as file:
            rawTrials = json.load(file)["studies"]

            trials = [Trial(rawJSON=rawTrial, verbose=True) for rawTrial in rawTrials]
            for trial in trials:
                trial.finishTranslation(verbose=True)
                # Convert trials to JSON serializable format
            trials_json = [trial.toJSON() for trial in trials]
            # Write trials to a JSON file
            with open("serializedCHIATrials.json", "w") as outfile:
                json.dump({"trials": trials_json}, outfile, indent=4)