import operator
import os
from typing import Any
import AI

import requests
import pymongo
from collections import defaultdict
import json


class Database:

    def __init__(self, client_uri="mongodb://localhost:27017/", database_name="ClinicalTrialsDB", JSON_collection_name="ClinicalTrialsJSON", MQL_collection_name="ClinicalTrialsMQL", PropertyCount_collection_name="PropertyCount"):
        self.client_uri = client_uri
        self.database_name = database_name

        self.JSON_collection_name = JSON_collection_name
        self.MQL_collection_name = MQL_collection_name
        self.PropertyCount_collection_name = PropertyCount_collection_name
        self.collection_name = JSON_collection_name

        self.connectToMongoDB()

        if self.collection.count_documents({}) == 0:
            self.importJSONData()

        self.collection = self.database[self.MQL_collection_name]

        if self.collection.count_documents({}) == 0:
            print("Translating all trials to MQL")
            self.translateAllTrialsToMQL()

    def translateOneTrialToMQL(self, doc):
        try:
            criteriaText = doc["eligibilityModule"]
        except KeyError:
            print("eligibilityModule not found in document")
            return None

        # add functionality to include the rest of the things in eligibility module later
        criteriaMQL = AI.TranslateTextToMQL(str(criteriaText))
        if criteriaMQL is None:
            print("Failed to properly translate to MQL")
            return None

        criteriaMQL = {
            "nctid": doc["nctId"],
            "title": doc["officialTitle"],
            **criteriaMQL
        }
        return criteriaMQL

    def updateDocumentsWithOldPropertyName(self, oldPropertyName, newPropertyName):
        # documentsToUpdate = self.collection.find(
        #     {oldPropertyName: {"$exists": True}})
        # for doc in documentsToUpdate:
        #     doc[newPropertyName] = doc.pop(oldPropertyName)
        #     self.collection.replace_one({"_id": doc["_id"]}, doc)
        query = {oldPropertyName: {"$exists": True}}
        update = {"$rename": {oldPropertyName: newPropertyName}}
        self.collection.update_many(query, update)

    def translateAllTrialsToMQL(self) -> None:
        self.collection = self.database[self.MQL_collection_name]

        alltrials = self.database[self.JSON_collection_name].find(projection={
            "nctId": 1, "officialTitle": 1, "eligibilityModule": 1})
        allProperties = {}
        for trial in alltrials:
            currentTrial = self.translateOneTrialToMQL(trial)
            if currentTrial is None:
                print("Failed to translate trial to MQL")
                continue
            self.collection.insert_one(currentTrial)

        try:
            allProperties: dict[str, int] = self.count_properties()
            print("\n\n\nAll properties now is ", dict(sorted(allProperties.items(),
                                                              key=operator.itemgetter(1))), "\n\n\n")
            self.database[self.PropertyCount_collection_name].insert_one(
                allProperties)
        except:
            print("Your code still sucks for counting properties")
            return

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

    def count_properties(self) -> dict[str, int]:
        property_counts: dict[str, int] = {}

        # Get all MQL documents from the database
        mql_documents = self.database[self.MQL_collection_name].find()

        # Loop through each MQL document
        for mql_document in mql_documents:
            # Recursively iterate through the document and count the occurrences of each property
            property_counts = add_dictionaries(
                countPropertiesInDoc(mql_document), property_counts,)

        return property_counts

# right now this does not double count properties that show up twice in an or statement.


def countPropertiesInDoc(document: dict[str, Any]) -> dict[str, int]:
    property_counts: dict[str, int] = {}

    def recurse(current):
        if isinstance(current, dict):
            for key, value in current.items():
                property_counts[key] = 1
                recurse(value)

        elif isinstance(current, list):
            for item in current:
                recurse(item)

    recurse(document)

    unImportantProperties: list[str] = ["_id", "nctid",
                                        "title"]
    importantPropertyCounts = {}
    for property_name, count in property_counts.items():
        if property_name not in unImportantProperties and not (isinstance(property_name, str) and property_name.startswith("$")):
            importantPropertyCounts[property_name] = count

    return importantPropertyCounts


# if you want to make this efficient then d1 should be the smaller one and d2 should be the larger more encompassing one
def add_dictionaries(d1: dict, d2: dict) -> dict:
    for property in d1:
        if property in d2:
            d2[property] += d1[property]
        else:
            d2[property] = d1[property]
    return d2
