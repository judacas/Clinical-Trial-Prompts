"""Database.py

This module provides functionality for interacting with a MongoDB database 
to store and query clinical trial data.

Classes:

Database: Handles connecting to MongoDB, importing/exporting data, and 
         translating documents between JSON and MQL formats.

Functions:

count_properties: Recursively counts property occurrences in a document.

add_dictionaries: Merges two dictionaries by adding values for shared keys.

The Database class is the primary interface for working with the database.
Key capabilities:

- Connect to a MongoDB database and access collections.
- Import clinical trial JSON data from a file or API.
- Translate individual docs between JSON and MQL format.
- Translate all docs in a collection between JSON and MQL.  
- Export docs from MongoDB back to the filesystem as JSON.
- Get a count of all properties used across documents.

The count_properties and add_dictionaries functions are helpers for 
tallying property usage and combining results.

Typical usage often involves:

1. Instantiating a Database object to connect to MongoDB.
2. Importing JSON data into the desired collection. 
3. Translating the collection docs to MQL format.
4. Exporting the collection back to JSON.

"""
import json
import operator
import os
from datetime import datetime
from typing import Any
from urllib import response

import AI
import pymongo
import requests

trialsToUse = ["03834493", "03426891", "04579380", "01810913",
               "04511013", "04614103", "04671667", "04614103", "04092283", "02339571"]


class Database:
    date_suffix = datetime.now().strftime("%m.%d.%y")

    def __init__(self, client_uri="mongodb://localhost:27017/",
                 database_name="ClinicalTrialsDB",
                 JSON_collection_name=f"CTJSON{date_suffix}",
                 badMQL_collection_name=f"CTBadMQL{date_suffix}",
                 MQL_collection_name=f"CTMQL{date_suffix}",
                 boolean_collection_name=f"CTBoolean{date_suffix}", property_collection_name=f"CTTotalProperties{date_suffix}"):
        self.client_uri = client_uri
        self.database_name = database_name
        self.JSON_collection_name = JSON_collection_name
        self.MQL_collection_name = MQL_collection_name
        self.boolean_collection_name = boolean_collection_name
        self.badMQL_collection_name = badMQL_collection_name
        self.PropertyCount_collection_name = property_collection_name
        self.collection_name = JSON_collection_name

        self.connectToMongoDB()

        if self.collection.count_documents({}) == 0:
            self.importJSONData()

        self.collection = self.database[self.MQL_collection_name]

        if self.collection.count_documents({}) == 0:
            print("Translating all trials to MQL")
            self.translateAllTrialsToMQL()

        self.export_mongo_to_json()

    def change_collection(self, new_collection_name):
        self.collection_name = new_collection_name
        self.collection = self.database[self.collection_name]

    def translateOneTrialToMQL(self, doc):
        try:
            # print(doc)
            criteriaText = doc["protocolSection"]["eligibilityModule"]["eligibilityCriteria"]
        except KeyError:
            print("eligibilityModule not found in document")
            return

        try:
            currentId = doc["protocolSection"]["identificationModule"]["nctId"]
            currentTitle = doc["protocolSection"]["identificationModule"]["officialTitle"]
        except KeyError:
            print("identification information not found in document")
            currentId = "NotValidNCTId"
            currentTitle = "NotValidTitle"

        # add functionality to include the rest of the things in eligibility module later
        criteriaBool, criteriabadMQL, criteriaMQL = AI.TranslateTextToMQL(
            str(criteriaText))
        if criteriaBool is None:
            print("Failed to properly translate to Boolean Algebra")
            return

        self.change_collection(self.boolean_collection_name)
        booleanJSON = {"nctId": currentId, "title": currentTitle,
                       "booleanRepresentation": criteriaBool}
        self.collection.insert_one(booleanJSON)

        if criteriabadMQL is None:
            print("Failed to properly translate to MQL")
            return

        self.change_collection(self.badMQL_collection_name)
        try:
            badMQLJSON = json.loads(criteriabadMQL)
            badMQLJSON["nctId"] = currentId
            badMQLJSON["title"] = currentTitle
            self.collection.insert_one(badMQLJSON)
        except ValueError:
            badMQLJSON = {"nctId": currentId, "title": currentTitle,
                          "Not yet fixed MQL": criteriabadMQL}
            self.collection.insert_one(badMQLJSON)

        if criteriaMQL is None:
            print("Failed to properly assert MQL adheres to JSON rules")
            return

        self.change_collection(self.MQL_collection_name)
        self.collection.insert_one(criteriaMQL)

        criteriaMQL = {
            "nctId": currentId,
            "title": currentTitle,
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

        alltrials = self.database[self.JSON_collection_name].find()
        allProperties = {}
        for trial in alltrials:
            self.translateOneTrialToMQL(trial)

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
            Database.fetch_clinical_trials(trials=trialsToUse)

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

    def get_official_titles(self):
        if self.collection is None:
            print("Collection is not set")
            raise ValueError("Collection is not set")

        cursor = self.collection.find({}, {"_id": 0, "officialTitle": 1})
        official_titles = [doc["officialTitle"] for doc in cursor]

        return official_titles

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

    # NOTE: this is super sloppy rn and doesn't use correct oop priniciples, only temporary solution to quickly export all the documents in the database

    def export_mongo_to_json(self):
        db = self.database
        print(db.list_collection_names())
        for collection_name in db.list_collection_names():
            if collection_name == self.PropertyCount_collection_name:
                print("Skipping PropertyCount collection")
                continue
            collection = db[collection_name]
            collection_path = os.path.join(self.database_name, collection_name)
            os.makedirs(collection_path, exist_ok=True)

            for document in collection.find():
                try:
                    docID = str(document["protocolSection"]
                                ["identificationModule"]["nctId"])
                except KeyError:
                    try:
                        docID = str(document["nctId"])
                    except KeyError:
                        print("Document does not have nctID or nctid")
                        docID = "NotValidNCTID" + str(document["_id"])
                document_path = os.path.join(collection_path, f"{docID}.json")
                document["_id"] = str(document["_id"])
                with open(document_path, "w") as f:
                    json.dump(document, f)

    @staticmethod
    def fetch_clinical_trials(trials=None):
        if trials is not None:
            totalTrials = []

            # NOTE:This will change the structure ofthe jsons to a more correct nested json, it will no longer work with previous code
            for trial in trials:
                response = requests.get(
                    f"""https://clinicaltrials.gov/api/v2/studies/NCT{trial}?format=json&fields=NCTId%2CEligibilityModule%2CBriefTitle%2COfficialTitle%2CBriefSummary%2CDetailedDescription""")
                print(response)
                totalTrials.append(response.json())

            with open("clinical_trials_simplified.json", "w") as f:
                json.dump(totalTrials, f)
            return

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
