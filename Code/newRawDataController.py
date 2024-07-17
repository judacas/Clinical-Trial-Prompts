import json
import os
import re
from typing import Any, Dict
from errorManager import logError
import requests


def curlWithStatusCheck(url: str) -> dict:
    response = requests.get(url, timeout=10)
    if response.status_code != 200:
        print("Something Went Wrong")
        print(response.text)
        logError(customText="Something Went Wrong with the ClinicalTrials API", e=response.text, during="curlWithStatusCheck")
        raise Exception("Something Went Wrong with the ClinicalTrials API")

    return response.json()


def split_criteria(criteria):
    # Split the criteria string using newline, *, and ordered list as delimiters
    return [
        x.strip()
        for x in re.split("\\*|^\\d+[.)]", criteria, flags=re.MULTILINE)
        if x != ""
    ]


def saveRandomTrialsToFile(n):
    with open("trials.json", "w") as f:
        json.dump(getRandomCancerTrials(n), f, indent=4)


def saveTrialToFile(trial: dict, folder, suffix = ""):
    print(json.dumps(trial, indent=4))
    fileName = os.path.join(folder, trial['nctId']) 
    fileName += suffix + ".json" if suffix != "" else ".json"
    with open(fileName, "w") as f:
        json.dump(trial, f, indent=4)


# ! WARNING: some IDs from chia are apparently invalid and will make it return an empty json but still 200 status code. there is definitely one wrong in the first ten
def getChiaIDs(n, start_index=0):
    directory = os.path.join(os.path.dirname(os.getcwd()), "CHIA")
    pattern = re.compile(r"NCT\d{8}")
    files = os.listdir(directory)

    # Filter files that match the pattern and remove duplicates
    ids = list(
        set([pattern.match(file).group() for file in files if pattern.match(file)])  # type: ignore .group wont get called if it doesn't match due to the if so not a problem
    )
    # ? for some reason it doesn't return them in the same order as in the directory normally but the zip file is sorted so just sort here and it will match the zip file
    ids.sort()

    return ids[start_index : start_index + n]


def getTrialsByID(trialIDS: list):
    allTrials = {}
    for i in range(0, len(trialIDS), 100):
        trialsAsQuery = "%2C+".join(trialIDS[i : min(i + 100, len(trialIDS))])
        currentTrials = curlWithStatusCheck(
            f"https://clinicaltrials.gov/api/v2/studies?format=json&fields=EligibilityModule%7CNCTId%7COfficialTitle&query.cond={trialsAsQuery}"
        )

        nextPageToken = currentTrials.get("nextPageToken", None)
        while nextPageToken:
            nextPageTrials = curlWithStatusCheck(
                f"https://clinicaltrials.gov/api/v2/studies?format=json&fields=EligibilityModule%7CNCTId%7COfficialTitle&query.cond={trialsAsQuery}&pageToken={nextPageToken}"
            )
            currentTrials["studies"].extend(nextPageTrials["studies"])
            nextPageToken = nextPageTrials.get("nextPageToken", None)
        if allTrials:
            allTrials["studies"].extend(currentTrials["studies"])
        else:
            allTrials = currentTrials

    filteredTrials = [
        preProcessTrial(trial["protocolSection"])
        for trial in allTrials["studies"]
    ]
    return filteredTrials

def saveTrialsToFile(trialIDS: list, folder: str, suffix = ""):
    trials = getTrialsByID(trialIDS)
    for trial in trials:
        saveTrialToFile(trial, folder, suffix=suffix)

def saveCHIATrials(n, folder, start_index=0, suffix = ""):
    Trials = getTrialsByID(getChiaIDs(n, start_index))
    for trial in Trials:
        saveTrialToFile(trial, folder, suffix=suffix)

def getRandomCancerTrials(n: int) -> dict:
    if n < 1 or n > 1000:
        raise ValueError(
            "n must be between 1 and 1000, well it can be over 1,000 but I haven't implemented pagination yet so get to work then"
        )
    data = curlWithStatusCheck(
        f"https://clinicaltrials.gov/api/v2/studies?format=json&query.cond=Cancer&query.intr=Intervention&fields=EligibilityModule%7CNCTId%7COfficialTitle&pageSize={n}"
    )
    if "nextPageToken" in data:
        del data["nextPageToken"]

    for i in range(len(data["studies"])):
        data["studies"][i] = preProcessTrial(
            data["studies"][i]["protocolSection"]
        )

    return data


def preProcessTrial(study):
    eligibilityModule: Dict[Any, Any] = study["eligibilityModule"]
    criteria: str = eligibilityModule["eligibilityCriteria"]
    inclusion_index = criteria.lower().find("inclusion criteria")
    exclusion_index = criteria.lower().find("exclusion criteria")
    if inclusion_index != -1 and exclusion_index != -1:
        eligibilityModule["inclusionCriteria"] = criteria[
            inclusion_index + 19 : exclusion_index
        ].strip()
        eligibilityModule["exclusionCriteria"] = criteria[
            exclusion_index + 19 :
        ].strip()
    elif inclusion_index != -1:
        eligibilityModule["inclusionCriteria"] = criteria[
            inclusion_index + 19 :
        ].strip()
    elif exclusion_index != -1:
        eligibilityModule["exclusionCriteria"] = criteria[
            exclusion_index + 19 :
        ].strip()
    else:
        eligibilityModule["Criteria"] = criteria.strip()

    eligibilityModule.pop("eligibilityCriteria", None)
    eligibilityModule.pop("samplingMethod", None)
    eligibilityModule.pop("studyPopulation", None)

    # Get the values of the fields
    healthy_volunteers = eligibilityModule.pop("healthyVolunteers", None)
    sex = eligibilityModule.pop("sex", None)
    minimum_age = eligibilityModule.pop("minimumAge", None)
    maximum_age = eligibilityModule.pop("maximumAge", None)
    std_ages = eligibilityModule.pop("stdAges", None)

    # Add the fields to inclusionCriteria or exclusionCriteria based on their truth values
    if healthy_volunteers is not None and healthy_volunteers == "false":
        eligibilityModule.setdefault("exclusionCriteria", "")
        eligibilityModule["exclusionCriteria"] += "\n* " + (
            "No healthy volunteers allowed"
        )

    if sex is not None and sex != "ALL":
        eligibilityModule.setdefault("inclusionCriteria", "")
        eligibilityModule["inclusionCriteria"] += "\n* " + (f"Must be {sex}")

    if minimum_age is not None:
        eligibilityModule.setdefault("inclusionCriteria", "")
        eligibilityModule["inclusionCriteria"] += "\n* " + (
            f"Must have minimum age of {minimum_age}"
        )

    if maximum_age is not None:
        eligibilityModule.setdefault("inclusionCriteria", "")
        eligibilityModule["inclusionCriteria"] += "\n* " + (
            f"Must have maximum age of {maximum_age}"
        )

    if std_ages and not minimum_age and not maximum_age:
        minAge: int = 0
        maxAge: int = 100
        notAdultEdgeCase = False
        if len(std_ages) == 1:
            if "OLDER_ADULT" in std_ages:
                minAge = 65
            if "ADULT" in std_ages:
                minAge = 18
                maxAge = 65
            if "CHILD" in std_ages:
                minAge = 0
        elif len(std_ages) == 2:
            if "OLDER_ADULT" not in std_ages:
                maxAge = 65
            if "ADULT" not in std_ages:
                notAdultEdgeCase = True
            if "CHILD" not in std_ages:
                minAge = 18
        if notAdultEdgeCase:
            eligibilityModule.setdefault("inclusionCriteria", "")
            eligibilityModule["inclusionCriteria"].append(
                "Must be between the age of 18 and 65"
            )
        else:
            if minAge != 0:
                eligibilityModule.setdefault("inclusionCriteria", "")
                eligibilityModule["inclusionCriteria"].append(
                    f"Must be {minAge} or older"
                )
            if maxAge != 100:
                eligibilityModule.setdefault("inclusionCriteria", "")
                eligibilityModule["inclusionCriteria"].append(
                    f"Must be {maxAge} or younger"
                )

    simpleStudy = {**study["identificationModule"], **study["eligibilityModule"]}
    return simpleStudy
