import json

json_file_path = "clinical_trials_simplified.json"

# Load the JSON data from the file
with open(json_file_path, encoding="utf-8") as f:
    data = f.read()
    print(data)
