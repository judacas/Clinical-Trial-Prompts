# import json
# import AI
import Database as db
import operator


def main():

    # Connect to the database
    myDB = db.Database("mongodb://localhost:27017/",
                       "ClinicalTrialsDB", "ClinicalTrialsJSON")

    propertyCount = myDB.count_properties()
    sorted_dict = dict(sorted(propertyCount.items(),
                       key=operator.itemgetter(1)))
    print(sorted_dict)
    # Get the current trial
    # currentTitle = myDB.get_official_titles()[0]
    # document = myDB.collection.find_one({"officialTitle": currentTitle})

    # If the trial is not found, print an error message
    # if document is None:
    #     print("Document not found")
    #     return

    # Convert the document to a JSON object
    # document["_id"] = str(document["_id"])
    # json_document = json.dumps(document)

    # # Get the description of the document
    # description = AI.GetDescription("five year old", json_document)
    # print(description)


if __name__ == "__main__":
    main()
