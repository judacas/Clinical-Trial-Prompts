import json
from trial import Trial
from concurrent.futures import ThreadPoolExecutor
def main():
    

    with open('trials.json') as file:
        rawTrials = json.load(file)["studies"]

        with ThreadPoolExecutor() as executor:
            trials = list(executor.map(Trial, rawTrials))

if __name__ == '__main__':
    main()