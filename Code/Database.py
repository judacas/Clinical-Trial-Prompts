import os
import AI

import requests
import pymongo
from collections import defaultdict
import json


class Database:

    def __init__(self, client_uri="mongodb://localhost:27017/", database_name="ClinicalTrialsDB", JSON_collection_name="ClinicalTrialsJSON", MQL_collection_name="ClinicalTrialsMQL"):
        self.client_uri = client_uri
        self.database_name = database_name
        self.JSON_collection_name = JSON_collection_name
        self.MQL_collection_name = MQL_collection_name
        self.collection_name = JSON_collection_name

        self.connectToMongoDB()

        if self.collection.count_documents({}) == 0:
            self.importJSONData()

        self.collection = self.database[self.MQL_collection_name]

        if self.collection.count_documents({}) == 0:
            print("Translating all trials to MQL")
            self.translateAllTrialsToMQL()

    def translateOneTrialToMQL(self, doc):
        # doc.pop("_id", None)
        # mql = json.dumps(doc)
        # mql = json.loads(mql)
        try:
            criteriaText = doc["eligibilityModule"]
        except KeyError:
            print("eligibilityModule not found in document")
            return
        print(criteriaText)

        # add functionality to include the rest of the things in eligibility module later
        criteriaMQL = AI.TranslateTextToMQL(str(criteriaText))

        tries = 3

        for i in range(tries+1):
            try:
                criteriaMQL = json.loads(criteriaMQL)
                break
            except:
                if i != tries:
                    print(
                        f"\n\n\nFailed to  convert to json\n\n\nAttempting to fix json, try: {i}\n\n\n")
                    criteriaMQL = AI.FixJSON(criteriaMQL)
        else:
            print(
                f"\n\n\nFailed to convert to json\n\n\n{criteriaMQL}\n\n\n")
            return None

        criteriaMQL = {
            "nctid": doc["nctId"],
            "title": doc["officialTitle"],
            **criteriaMQL
        }
        try:
            self.database[self.MQL_collection_name].insert_one(criteriaMQL)
        except Exception as e:
            print(
                f"Error inserting document into {self.MQL_collection_name}: {e}")

    def translateAllTrialsToMQL(self):
        self.collection = self.database[self.MQL_collection_name]
        if self.collection is None:
            print("Collection is not set")
            raise ValueError("Collection is not set")

        alltrials = self.database[self.JSON_collection_name].find(projection={
            "nctId": 1, "officialTitle": 1, "eligibilityModule": 1})
        for trial in alltrials:
            currentTrial = self.translateOneTrialToMQL(trial)
            if currentTrial is not None:
                self.collection.insert_one(currentTrial)

        # mqldocuments = map(self.translateOneTrialToMQL, alltrials)

    def connectToMongoDB(self):
        self.client = pymongo.MongoClient(self.client_uri)

        self.database = self.client[self.database_name]

        self.collection = self.database[self.collection_name]

    def importJSONData(self, json_file_path="clinical_trials_simplified.json"):

        # Check if the JSON file exists, otherwise fetch it from clinical trials.org
        if not os.path.exists(json_file_path):
            Database.fetch_clinical_trials()

        # Load the JSON data from the file
        with open(json_file_path) as f:
            data = json.load(f)

        # print(data)
        # Insert the data into the collection
        if self.collection is None:
            print("Collection is not set")
            raise ValueError("Collection is not set")

        self.collection.insert_many(data)

        # Print a message to confirm that the data was imported
        print(
            f"Imported {len(data)} documents into {self.database_name}.{self.collection_name}")

    @staticmethod
    def fetch_clinical_trials():
        url = "https://clinicaltrials.gov/api/v2/studies?format=json&query.parser=simple&query.cond=Cancer&query.locn=Moffitt+Cancer+Center&query.intr=Intervention"

        # OLD WAY TO GET API REQUEST NOT USING REQUESTS
        # headers = {"accept": "application/json"}
        # result = subprocess.run(["curl", "-X", "GET", url, "-H",
        #                         f"accept: {headers['accept']}"], capture_output=True, text=True)

        # if result.returncode != 0:
        #     # Error
        #     print("Getting clinical trial data did not work")
        #     print(result.stderr)
        #     return

        result = requests.get(url)

        # Success
        print("it worked")
        # data = json.loads(result.stdout)
        data = result.json()
        trials = []
        for study in data['studies']:
            trial = {
                'nctId': study['protocolSection']['identificationModule'].get('nctId'),
                'briefTitle': study['protocolSection']['identificationModule'].get('briefTitle'),
                'officialTitle': study['protocolSection']['identificationModule'].get('officialTitle'),
                'briefSummary': study['protocolSection']['descriptionModule'].get('briefSummary'),
                'detailedDescription': study['protocolSection']['descriptionModule'].get('detailedDescription'),
                'eligibilityModule': study['protocolSection'].get('eligibilityModule')
            }
            trials.append(trial)
        with open("clinical_trials_simplified.json", "w") as f:
            json.dump(trials, f)

    def get_official_titles(self):
        if self.collection is None:
            print("Collection is not set")
            raise ValueError("Collection is not set")

        cursor = self.collection.find({}, {"_id": 0, "officialTitle": 1})
        official_titles = [doc["officialTitle"] for doc in cursor]

        return official_titles

    def change_collection(self, new_collection_name):
        self.collection_name = new_collection_name
        self.collection = self.database[self.collection_name]

    from collections import defaultdict

    def count_properties(self):
        property_counts = {}

        # Get all MQL documents from the database
        mql_documents = self.database[self.MQL_collection_name].find()

        # Loop through each MQL document
        for mql_document in mql_documents:
            # Recursively iterate through the document and count the occurrences of each property
            property_counts = add_dictionaries(
                property_counts, countPropertiesInDoc(mql_document))

        unImportantProperties = ["_id", "nctid",
                                 "title", "$and", "$or", "$not"]

        for property in unImportantProperties:
            if property in property_counts:
                property_counts.pop(property)

        return property_counts


def countPropertiesInDoc(document):
    property_counts = {}
    for property_name, value in document.items():
        # If the property is not already in the dictionary, add it with a count of 1
        if property_name not in property_counts:
            property_counts[property_name] = 1
        # If the property is already in the dictionary, increment its count by 1
        else:
            property_counts[property_name] += 1
        # If the value is a dictionary, recursively count its properties
        # Print the type of the value
        # print(f"{property_name} is {type(value)}")
        if isinstance(value, list):
            for item in value:
                property_counts = add_dictionaries(
                    property_counts, countPropertiesInDoc(item))

    return property_counts


def add_dictionaries(d1, d2):
    result = defaultdict(int)
    for key, value in d1.items():
        result[key] += value
    for key, value in d2.items():
        result[key] += value
    return result
