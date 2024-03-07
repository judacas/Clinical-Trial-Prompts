import json
import re
from typing import Any, Dict
import requests


def split_criteria(criteria):
    # Split the criteria string using newline, *, and ordered list as delimiters
    return [
        x.strip()
        for x in re.split("\\*|^\\d+[.)]", criteria, flags=re.MULTILINE)
        if x != ""
    ]


def split_and_preserve_indentation(text):
    lines: list[str] = text.split("\n")
    blocks = []
    current_block = None

    for line in lines:
        if line == "":  # line is empty
            continue
        line = re.sub(
            r"^(\*\s+|\d+\.\s+)", "", line
        )  # remove asterisk or numbered list at the beginning
        if line.startswith("  "):  # line is indented
            if current_block is not None:
                current_block += "\n\t" + line.strip()
        else:  # line is not indented
            if current_block is not None:
                blocks.append(current_block)
            current_block = line.strip()

    if current_block is not None:
        blocks.append(current_block)

    return blocks


def saveTrialsToFile(n):
    with open("trials.json", "w") as f:
        json.dump(getTrials(n), f, indent=4)

def getTrials(n: int) -> dict:
    if n < 1 or n > 1000:
        raise ValueError(
            "n must be between 1 and 1000, well it can be over 1,000 but I haven't implemented pagination yet so get to work then"
        )
    response = requests.get(
        f"https://clinicaltrials.gov/api/v2/studies?format=json&query.cond=Cancer&query.intr=Intervention&fields=EligibilityModule%7CNCTId%7COfficialTitle&pageSize={n}",
        timeout=10,
    )
    if response.status_code != 200:
        print("Something Went Wrong")
        print(response.text)
        raise Exception("Something Went Wrong with the ClinicalTrials API")
    data = response.json()
    if "nextPageToken" in data:
        del data["nextPageToken"]

    for i in range(len(data["studies"])):
        data["studies"][i] = NoSplitingProcessCriteria(
            data["studies"][i]["protocolSection"]
        )
        
    return data

def formatJSON(jsonObj: dict)-> str:
    formatted_json = json.dumps(jsonObj, indent=4)
    return (
        formatted_json.replace("\\n  ", "\n\t")
        .replace("\\n", "\n")
        .replace("\\t", "\t")
        .replace("\\*", "note: ")
    )

def ProccessCriteria(study):
    eligibilityModule: Dict[Any, Any] = study["eligibilityModule"]
    criteria: str = eligibilityModule["eligibilityCriteria"]

    blocks = split_and_preserve_indentation(criteria)
    print(criteria)
    print(blocks)

    inclusion_index = -1
    exclusion_index = -1
    j = 0
    while j < len(blocks):
        if "inclusion criteria" in blocks[j].lower():
            inclusion_index = j
            blocks.pop(j)

        elif "exclusion criteria" in blocks[j].lower():
            exclusion_index = j
            blocks.pop(j)
        else:
            j += 1

    if inclusion_index != -1 and exclusion_index != -1:
        eligibilityModule["inclusionCriteria"] = blocks[inclusion_index:exclusion_index]
        eligibilityModule["exclusionCriteria"] = blocks[exclusion_index:]
    elif inclusion_index != -1:
        eligibilityModule["inclusionCriteria"] = blocks[inclusion_index:]
    elif exclusion_index != -1:
        eligibilityModule["exclusionCriteria"] = blocks[exclusion_index:]
    else:
        eligibilityModule["Criteria"] = blocks

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
        eligibilityModule["exclusionCriteria"].append("No healthy volunteers allowed")

    if sex is not None and sex != "ALL":
        eligibilityModule["inclusionCriteria"].append(f"Must be {sex}")

    if minimum_age is not None:
        eligibilityModule["inclusionCriteria"].append(
            f"Must have minimum age of {minimum_age}"
        )

    if maximum_age is not None:
        eligibilityModule["inclusionCriteria"].append(
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
            eligibilityModule["inclusionCriteria"].append(
                "Must be between the age of 18 and 65"
            )
        else:
            if minAge != 0:
                eligibilityModule["inclusionCriteria"].append(
                    f"Must be {minAge} or older"
                )
            if maxAge != 100:
                eligibilityModule["inclusionCriteria"].append(
                    f"Must be {maxAge} or younger"
                )

    return study


def NoSplitingProcessCriteria(study):
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
        eligibilityModule["exclusionCriteria"] += "\n* " + (
            "No healthy volunteers allowed"
        )

    if sex is not None and sex != "ALL":
        eligibilityModule["inclusionCriteria"] += "\n* " + (f"Must be {sex}")

    if minimum_age is not None:
        eligibilityModule["inclusionCriteria"] += "\n* " + (
            f"Must have minimum age of {minimum_age}"
        )

    if maximum_age is not None:
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
            eligibilityModule["inclusionCriteria"].append(
                "Must be between the age of 18 and 65"
            )
        else:
            if minAge != 0:
                eligibilityModule["inclusionCriteria"].append(
                    f"Must be {minAge} or older"
                )
            if maxAge != 100:
                eligibilityModule["inclusionCriteria"].append(
                    f"Must be {maxAge} or younger"
                )

    return study


# NOTE: there can be instances where they use a * and its not a bullet point, its denoted by \\* but I think this is rare enough that we can ignore it for now
def preProcessData(data):
    # Split eligibility criteria into inclusion and exclusion
    for i in range(len(data["studies"])):
        study = data["studies"][i]["protocolSection"]
        eligibilityModule: Dict[Any, Any] = study["eligibilityModule"]
        criteria: str = eligibilityModule["eligibilityCriteria"]

        inclusion_index = criteria.lower().find("inclusion criteria")
        exclusion_index = criteria.lower().find("exclusion criteria")
        if inclusion_index != -1 and exclusion_index != -1:
            eligibilityModule["inclusionCriteria"] = split_criteria(
                criteria[inclusion_index + 19 : exclusion_index].strip(" \n*:")
            )
            eligibilityModule["exclusionCriteria"] = split_criteria(
                criteria[exclusion_index + 19 :].strip(" \n*:")
            )
        elif inclusion_index != -1:
            eligibilityModule["inclusionCriteria"] = split_criteria(
                criteria[inclusion_index + 19 :].strip(" \n*:")
            )
        elif exclusion_index != -1:
            eligibilityModule["exclusionCriteria"] = split_criteria(
                criteria[exclusion_index + 19 :].strip(" \n*:")
            )
        else:
            eligibilityModule["Criteria"] = split_criteria(criteria.strip(" \n*:"))

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
            eligibilityModule["exclusionCriteria"].append(
                "No healthy volunteers allowed"
            )

        if sex is not None and sex != "ALL":
            eligibilityModule["inclusionCriteria"].append(f"Must be {sex}")

        if minimum_age is not None:
            eligibilityModule["inclusionCriteria"].append(
                f"Must have minimum age of {minimum_age}"
            )

        if maximum_age is not None:
            eligibilityModule["inclusionCriteria"].append(
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
                eligibilityModule["inclusionCriteria"].append(
                    "Must be between the age of 18 and 65"
                )
            else:
                if minAge != 0:
                    eligibilityModule["inclusionCriteria"].append(
                        f"Must be {minAge} or older"
                    )
                if maxAge != 100:
                    eligibilityModule["inclusionCriteria"].append(
                        f"Must be {maxAge} or younger"
                    )
        data["studies"][i] = study
    return data



saveTrialsToFile(10)

# criteria =getTrials(1)["studies"][0]["eligibilityModule"]

# pyperclip.copy(formatJSON(criteria))
# print(formatJSON(criteria))
