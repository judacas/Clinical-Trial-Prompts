import json

import requests


def fetch_clinical_trials(trials=None):
    if trials is not None:
        totalTrials = []

        # NOTE:This will change the structure ofthe jsons to a more correct nested json, it will no longer work with previous code
        for trial in trials:
            response = requests.get(
                f"""https://clinicaltrials.gov/api/v2/studies/NCT{trial}?format=json&fields=NCTId%2CEligibilityModule%2CBriefTitle%2COfficialTitle%2CBriefSummary%2CDetailedDescription"""
            , timeout=10)
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

    result = requests.get(url, timeout=10)

    # Success
    print(result)
    # data = json.loads(result.stdout)
    
    data = result.json()
    trials = []
    for study in data["studies"]:
        trial = {
            "nctId": study["protocolSection"]["identificationModule"].get("nctId"),
            "briefTitle": study["protocolSection"]["identificationModule"].get(
                "briefTitle"
            ),
            "officialTitle": study["protocolSection"]["identificationModule"].get(
                "officialTitle"
            ),
            "briefSummary": study["protocolSection"]["descriptionModule"].get(
                "briefSummary"
            ),
            "detailedDescription": study["protocolSection"]["descriptionModule"].get(
                "detailedDescription"
            ),
            "eligibilityModule": study["protocolSection"].get("eligibilityModule"),
        }
        trials.append(trial)
    with open("clinical_trials_simplified.json", "w") as f:
        json.dump(trials, f)


fetch_clinical_trials()