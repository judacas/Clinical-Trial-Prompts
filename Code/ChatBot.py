import analyzer
from trial import Trial
from collections import defaultdict

# TODO Implement fully later once we need to talk with trials with updated structure. For now use the commit Clinical-Trial-Prompts-d5792dd78d94f8a2f0a9ae79159d9c8b14526303 to talk to the old structure
class ChatBot:
    def __init__(self, folder, trial_ids, patientData = None):
        self.folder = folder
        self.trial_ids = trial_ids
        self.trials: list[Trial] = [Trial(serializedJSON=trial) for trial in analyzer.getJSONSFromFolder(folder=folder, suffix="Raw",IDs=trial_ids)]
        self.idToTrial = {trial.nctId: trial for trial in self.trials}
        self.initializeNeededData()
        
    # This should def be in a database later once we get to large enough trials
    # Using list of dictionaries for now for simplicity
    def initializeNeededData(self):
        self.neededData = defaultdict(lambda: [])
        for trial in self.trials:
            criterions = trial.getCriterions()
            for criterion in criterions:
                self.neededData[criterion.text].append(criterion)
        
    # This will be much more complex later, just a filler for now since it should all eventually be in a database
    def getNextTopCriterions(self, n):
        return self.neededData[:n]
            

    def update_patient_data(self):
        # Implement the logic to update the data on the patient
        pass