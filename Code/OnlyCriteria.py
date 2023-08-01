import json
import subprocess
import os

url = "https://clinicaltrials.gov/api/v2/studies?format=json&query.parser=simple&query.cond=Cancer&query.locn=Moffitt+Cancer+Center&query.intr=Intervention"
headers = {"accept": "application/json"}

result = subprocess.run(["curl", "-X", "GET", url, "-H",
                        f"accept: {headers['accept']}"], capture_output=True, text=True)

if result.returncode != 0:
    # Error
    print("Getting clinical trial data did not work")
    print(result.stderr)
    exit(1)

# Success
print("it worked")
data = json.loads(result.stdout)
trials = []
for study in data['studies']:
    trial = {'criteria': study['protocolSection']
             ['eligibilityModule'].get('eligibilityCriteria')}
    print(trial)
    trials.append(trial)
with open("AllCancerEligibilty.json", "w") as f:
    json.dump(trials, f)
