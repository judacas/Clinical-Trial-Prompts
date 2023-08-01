# # Connect to the database
    # myDB = db.Database("mongodb://localhost:27017/",
    #                    "ClinicalTrialsDB", "ClinicalTrialsColl")

    # # Get the current trial
    # currentTitle = myDB.get_official_titles()[0]
    # document = myDB.collection.find_one({"officialTitle": currentTitle})

    # # If the trial is not found, print an error message
    # if document is None:
    #     print("Document not found")
    #     return

    # # Convert the document to a JSON object
    # document["_id"] = str(document["_id"])
    # json_document = json.dumps(document)