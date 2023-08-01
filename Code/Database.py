import json
import pymongo
import subprocess
import os

import requests


class Database:

    def __init__(self, client_uri, database_name, collection_name):
        self.client_uri = client_uri
        self.database_name = database_name
        self.collection_name = collection_name

        self.connectToMongoDB()

        if self.collection.count_documents({}) == 0:
            self.importJSONData()

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
