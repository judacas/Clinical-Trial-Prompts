import json
import re
from typing import Any, Dict
import requests

exampleEligibility = "Inclusion Criteria:\n\n* - Woman older than 18 years\n* Low-risk gestational trophoblastic neoplasia according to FIGO score (FIGO score ≤ 6) with indication of methotrexate as first line treatment\n* Patients with Eastern Cooperative Oncology Group (ECOG) performance status ≤ 2\n* Patients with adequate bone marrow function measured within 28 days prior to administration of study treatment as defined below\n\n  * Absolute granulocyte count ≥ 1.5 x 10 9 /L\n  * Platelet count ≥ 100 x 10 9 /L\n  * Haemoglobin ≥ 9.0 g/dL (may have been blood transfused)\n* Patients with adequate renal function:\n\n  \\* Calculated creatinine clearance ≥ 30 ml/min according to the Cockcroft-Gault formula (or local institutional standard method)\n* Patients with adequate hepatic function\n\n  \\*Serum bilirubin ≤ 1.5 x UNL and AST/ALT ≤ 2.5 X UNL (≤ 5 X UNL for patients with liver metastases)\n* Patients must have a life expectancy ≥ 16 weeks\n* Confirmation of non-childbearing status for women of childbearing potential.\n\nAn evolutive pregnancy can be ruled out in the following cases:\n\n* in case of a previous hysterectomy\n* if serum hCG level ≥ 2 000 IU/L and no intra or extra-uterine gestational sac is detected on pelvic ultrasound\n* if serum hCG level \\< 2 000 IU/L on a first measurement and serum hCG increases \\<100% on a second measurement performed 3 days later.\n\n  * Highly effective contraception if the risk of conception exists. (Note: The effects of the trial drug on the developing human fetus are unknown; thus, women of childbearing potential must agree to use 2 highly effective contraceptions, defined as methods with a failure rate of less than 1 % per year. Highly effective contraception is required at least 28 days prior, throughout and for at least 12 months after avelumab treatment.\n  * Patients who gave its written informed consent to participate to the study\n  * Patients affiliated to a social insurance regime\n  * Patient is willing and able to comply with the protocol for the duration of the treatment\n\nExclusion Criteria:\n\n* Prior therapy with an anti-PD-1, anti-PD-L1, anti-PD-L2, anti-CD137, or anti- CTLA 4 antibody (including ipilimumab, tremelimumab or any other antibody or drug specifically targeting T-cell costimulation or immune checkpoint pathways).\n* Illness, incompatible with avelumab, such as congestive heart failure; respiratory distress; liver failure; uncontrolled epilepsy; allergy.\n* Patients with a known allergic hypersensitivity to methotrexate or any of the other ingredients (sodium chloride, sodium hydroxide, and hydrochloric acid if excipient)\n* Patients with second primary cancer, except: adequately treated non-melanoma skin cancer, curatively treated in-situ cancer of the cervix, or other solid tumours curatively treated with no evidence of disease for ≥ 5 years.\n* All subjects with brain metastases, except those meeting the following criteria:\n\n  * Brain metastases that have been treated locally and are clinically stable for at least 2 weeks prior to enrolment, No ongoing neurological symptoms that are related to the brain localization of the disease (sequelae that are a consequence of the treatment of the brain metastases are acceptable).\n  * Subjects with brain metastases must be either off steroids except a stable or decreasing dose of \\<10mg daily prednisone (or equivalent).\n* Patients receiving any systemic chemotherapy, radiotherapy (except for palliative reasons), within 2 weeks from the last dose prior to study treatment (or a longer period depending on the defined characteristics of the agents used). The patient can receive a stable dose of bisphosphonates for bone metastases, before and during the study as long as these were started at least 4 weeks prior to treatment with study drug.\n* Persistent toxicities (\\>=CTCAE grade 2) with the exception of alopecia and sensory neuropathy, caused by previous cancer therapy.\n* Treatment with other investigational agents.\n* Bowel occlusive syndrome, inflammatory bowel disease, immune colitis, or other gastro-intestinal disorder that does not allow oral medication such as malabsorption.\n* Stomatitis, ulcers of the oral cavity and known active gastrointestinal ulcer disease\n* Clinically significant (i.e., active) and severe cardiovascular disease according to investigator opinion such as myocardial infarction (\\< 6 months prior to enrollment)\n* Patients with immune pneumonitis, pulmonary fibrosis\n* Known severe hypersensitivity reactions to monoclonal antibodies, any history of anaphylaxis, or uncontrolled asthma (ie, 3 or more features of partially controlled asthma Global Initiative for Asthma 2011).\n* Known human immunodeficiency virus (HIV) or acquired immunodeficiency syndrome (AIDS) related illness.\n* Active infection requiring systemic therapy.\n* Positive test for HBV surface antigen and / or confirmatory HCV RNA (if anti-HCV antibody tested positive)\n* Administration of a live vaccine within 30 days prior to study entry.\n* Current or prior use of immunosuppressive medication within 7 days prior to start of study treatment.\n\nThe following are exceptions to this exclusion criterion:\n\n* Intranasal, inhaled, topical steroids, or local steroid injections (eg, intra-articular injection);\n* Systemic corticosteroids at physiologic doses not to exceed 10 mg/day of prednisone or equivalent;\n* Steroids as premedication for hypersensitivity reactions (eg, CT scan premedication).\n\n  * Active autoimmune disease that might deteriorate when receiving an immunostimulatory agents.\n\nPatients with diabetes type I, vitiligo, psoriasis, hypo- or hyperthyroid disease not requiring immunosuppressive treatment are eligible.\n\n* Female patients who are pregnant or lactating, or are of childbearing potential and not practicing a medically acceptable method of birth control.\n* Treatment with oral anticoagulant such Coumadin.\n* Alcoholism (patient interview, investigator judgment)\n* Resting ECG with QTc \\> 470msec on 2 or more time points within a 24 hour period or family history of long QT syndrome. Torsades de Pointes, arrhythmias (including sustained ventricular tachyarrhythmia and ventricular fibrillation, bradycardia defined as \\<50 bpm), right bundle branch block and left anterior hemiblock (bifascicular block), unstable angina, coronary/peripheral artery bypass graft, symptomatic congestive heart failure (CHF New York Heart Association Class III or IV), cerebrovascular accident, transient ischemic attack or symptomatic pulmonary embolism.\n* Prior organ transplantation, including allogeneic stem cell transplantation (excluding autologous bone marrow transplant)\n* Patients under guardianship."


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
