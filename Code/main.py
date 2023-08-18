import json
import AI
import Database as db
# import operator


def main():

    # Connect to the database
    myDB = db.Database("mongodb://localhost:27017/",
                       "ClinicalTrialsDB", "ClinicalTrialsJSON")

    properties = myDB.count_properties()

    for key in properties:
        print(key, properties[key])

    # propertyCount = myDB.count_properties()

    # print(" | ".join(propertyCount.keys()))

    # print("\n\n\n\n")

    # sorted_dict = dict(sorted(propertyCount.items(),
    #                    key=operator.itemgetter(1)))
    # print(sorted_dict)

    # Get the current trial
    # currentTitle = myDB.get_official_titles()[0]
    # document = myDB.collection.find_one()

    # # If the trial is not found, print an error message
    # if document is None:
    #     print("Document not found")
    #     return

    # # Convert the document to a JSON object
    # document["_id"] = str(document["_id"])
    # json_document = json.dumps(document)

    # print("Document to be translated is:", json_document)
    # mql = myDB.translateOneTrialToMQL(document)
    # print("\n\n\n")
    # print(mql)
    # # Get the description of the document
    # description = AI.GetDescription("five year old", json_document)
    # print(description)


if __name__ == "__main__":
    main()
