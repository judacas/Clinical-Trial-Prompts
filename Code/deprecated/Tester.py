import json

from sympy import true
from trial import Trial
import newRawDataController as trialGetter

# print(trialGetter.getChiaIDs(10,10))
# trialGetter.saveCHIATrialsToFile(10,10)
# trial = {"studies": [trialGetter.getTrialByNCTID(trialGetter.getChiaIDs(1)[0]), "testTrial.json"]}
# print(trial)
# trialGetter.saveTrialToFile(trial, "testTrial.json")

# trialGetter.saveTrialToFile(trialGetter.processCriteria((trialGetter.getTrialsByID(trialGetter.getChiaIDs(1)))), "testTrial.json")



# trialGetter.saveTrialToFile(trialGetter.getTrialByNCTID(trialGetter.getChiaIDs(1)[0]), "testTrial.json")

trialGetter.saveCHIATrials(n=100, fileName="CHIAtrials.json")
# for id in trialGetter.getChiaIDs(1000):
#     print(id, end=", ")
# print(len(trialGetter.getChiaIDs(1000)))

with open("CHIATrials.json") as file:
            rawTrials = json.load(file)["studies"]

            trials = [Trial(rawJSON=rawTrial, verbose=True, runAllAtOnce=true) for rawTrial in rawTrials]
            for trial in trials:
                trial.finishTranslation(verbose=True)
                # Convert trials to JSON serializable format
            trials_json = [trial.toJSON() for trial in trials]
            # Write trials to a JSON file
            with open("first100SerializedCHIATrials4O.json", "w") as outfile:
                json.dump({"trials": trials_json}, outfile, indent=4)