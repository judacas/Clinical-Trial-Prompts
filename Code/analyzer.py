import glob
from typing import Any
from fuzzywuzzy import fuzz
import os
import re
from loguru import logger
from tabulate import tabulate
import sympy
from trial import Trial
import json
import newRawDataController as trialGetter
def processTrialsInFolder(folder):
    logger.trace("Processing trials in folder: ", folder)
    json_files = glob.glob(os.path.join(folder, "*.json"))
    logger.trace("Found", len(json_files), "files")
    processedTrials: dict = {"Trials": []}
    for json_file in json_files:
        logger.trace(os.path.basename(json_file))
        with open(json_file) as file:
            rawTrial = json.load(file)
            trial = Trial(rawJSON=rawTrial,verbose=True,)
            try:
                trial.finishTranslation(verbose=True)
                trial_json = trial.toJSON()
                processedTrials["Trials"].append(trial_json)
                trialGetter.saveTrialToFile(trial_json, folder, suffix="_Processed")
            except Exception as e:
                logger.error(f"Error processing trial {os.path.basename(json_file)}: {e}")
    return processedTrials
def updatedCompareToChia(ChiaFolder, personalFolder, isProcessed):
    trialIds = getNctIdsFromFolder(personalFolder)
    validTrials = []
    inValidTrials = []
    unReadableTrials = []
    extraCounter = 0
    for trial in trialIds:
        chiaCriteria: list[str] = getChiaCriteriaAsList(ChiaFolder, trial)
        personalCriteria: list[str] = getProcessedTrial(personalFolder, trial) if isProcessed else getRawTrialInFolder(personalFolder, trial)

        if not chiaCriteria:
            logger.warning(f"CHIA does not have criteria for {trial}")
            unReadableTrials.append(trial)
            continue
        if not personalCriteria:
            logger.warning(f"Personal does not have criteria for {trial}")
            unReadableTrials.append(trial)
            continue
        chiaCriteria = cleanLines(chiaCriteria)
        personalCriteria = cleanLines(personalCriteria)
        matches, leftOvers = updatedCompareLists(chiaCriteria, personalCriteria, 90)
        if not matches.count(""):
            validTrials.append(trial)
            extraCounter += len(leftOvers)
            
        else:
            inValidTrials.append(trial)
        printResults(trial, chiaCriteria, matches, list(leftOvers),isProcessed, personalFolder)
    resultsSummary = comparisonSummaryToJSON(len(trialIds), len(unReadableTrials), extraCounter, validTrials, inValidTrials)
    print("\n",json.dumps(resultsSummary, indent=4))
    with open (os.path.join(personalFolder, "comparisonSummary.json"), 'w', encoding='utf-8') as file:
        json.dump(resultsSummary, file, indent=4)
    
def comparisonSummaryToJSON(totalTrialNum, unReadableTrials, extraCriteria, validTrials, inValidTrials) -> dict[str, Any]:
    return {
        "Summary": {
            "Total Trials Analyzed": totalTrialNum,
            "Trials Unable to Test": unReadableTrials,
            "Trials Where at least all CHIA criterions were present": len(validTrials),
            "Trials That did NOT have All CHIA criterions": len(inValidTrials),
            "Total Extra Criteria (only from valid trials)": extraCriteria,
            "Average Extra Criteria per Trial": extraCriteria/len(validTrials) if validTrials else 0
        },
        "ValidTrials": validTrials,
        "InvalidTrials": inValidTrials
    }

def printResults(nctID, source: list[str], matches: list[str], leftOvers: list[str], isProcessed, folder=None):
    totalNotFound = matches.count("")
    totalFound = len(matches) - totalNotFound
    output = [
        f"\n\n{nctID} {'Processed' if isProcessed else 'Raw'} comparison:",
        "\nSummary:",
        f"CHIA has {len(source)} criteria while your personal folder has {len(matches) + len(leftOvers)} criteria",
        f"Total found criteria: {totalFound}/{len(source)}",
        f"Total not Found: {totalNotFound}/{len(source)}",
        f"Total Extra: {len(leftOvers)}",
        f"This trial is {'VALID' if totalNotFound == 0 else 'INVALID'}"
    ]
    for table in matchingResultsToTables(source, matches, leftOvers):
        output.extend(("\n\n", table))
    output_str = '\n'.join(output)

    if folder:
        filePath = os.path.join(folder, f"{nctID}_{'processed' if isProcessed else 'raw'}_comparison.txt")
        with open(filePath, 'w', encoding='utf-8') as file:
            file.write(output_str)

    print(output_str)

    
    
def matchingResultsToTables(source, matchingResults, leftOvers):
    found = [[source[i], matchingResults[i]] for i in range(len(source)) if matchingResults[i] != ""]
    notFound = [[source[i]] for i in range(len(source)) if matchingResults[i] == ""]
    extra = [[leftOver] for leftOver in leftOvers]

    found_table = tabulate(found, headers=['CHIA Criteria', 'Matching Personal Criteria'], tablefmt='fancy_grid', maxcolwidths=50) if found else "Nothing was Found"
    notFound_table = tabulate(notFound, headers=['CHIA Criteria Not Found in Personal'], tablefmt='fancy_grid', maxcolwidths=100) if notFound else "Everything was Found"
    extra_table = tabulate(extra, headers=['Extra Personal Criteria'], tablefmt='fancy_grid', maxcolwidths=100) if extra else "We had Nothing Extra"

    return found_table, notFound_table, extra_table    


def getChiaCriteriaAsList(ChiaFolder, nctId) -> list[str]:
    chiaCriterias: list[str] = []
    for criteria_type in ['inc', 'exc']:
        file_path = os.path.join(ChiaFolder, f"{nctId}_{criteria_type}.txt")
        try:
            with open(file_path, encoding='utf-8') as file:
                chiaCriterias.extend(cleanLines(file.read()))
        except FileNotFoundError:
            pass
        except UnicodeDecodeError:
            logger.warning(f"Couldn't read {criteria_type} criteria for {nctId}")
    return chiaCriterias
def getRawTrialInFolder(folder, nctId) -> list[str]:
    filePath = os.path.join(folder, f"{nctId}.json")
    criteria = ""
    try:
        with open(filePath, encoding='utf-8') as file:
            rawTrialJSON = json.load(file)
            if "inclusionCriteria" in rawTrialJSON:
                criteria+=f'\n{rawTrialJSON["inclusionCriteria"]}'
            if "exclusionCriteria" in rawTrialJSON:
                criteria+=f'\n{rawTrialJSON["exclusionCriteria"]}'
            if "Criteria" in rawTrialJSON:
                criteria+=f'\n{rawTrialJSON["Criteria"]}'
    except FileNotFoundError:
        logger.warning(f"Couldn't find Raw {nctId}")
    except Exception:
        logger.warning(f"Some error reading raw trial for {nctId}")
    return cleanLines(criteria)

def getProcessedTrial(folder, nctId) -> list[str]:
    filePath = os.path.join(folder, f"{nctId}_Processed.json")
    try:
        with open(filePath, encoding='utf-8') as file:
            trialJSON = json.load(file)
            trial = Trial(serializedJSON=trialJSON)
            return sympyExpressionStringToCriteriaList(trial.symPyExpression)
    except FileNotFoundError:
        logger.warning(f"{nctId} Processed file not found")
    except Exception:
        logger.warning(f"Error reading processed trial for {nctId}")
    return []
    
    

def sympyExpressionStringToCriteriaList(expressionString) -> list[str]:
    personalCriteriaExpression: sympy.Expr = sympy.sympify(expressionString)
    return cleanLines([str(crit) for crit in personalCriteriaExpression.free_symbols])
  
def updatedCompareLists(source: list[str], destination: list[str], threshold) -> tuple[list[str], set[str]]:
    if not isinstance(source, list) or not isinstance(destination, list):
        raise ValueError("source and destination must be lists of strings")
    if not source or not destination:
        raise ValueError("source and destination must not be empty")
    matches = []
    remainingDestination = set(destination)
    for item in source:
        bestScore = 0
        bestMatch = ""
        for dest in remainingDestination:
            score = fuzz.ratio(item, dest)
            if score > bestScore:
                bestScore = score
                bestMatch = dest
            if score == 100:
                break
        if bestScore >= threshold:
            remainingDestination.remove(bestMatch)
            matches.append(bestMatch)
        else:
            matches.append("")
    return matches, remainingDestination
        
def cleanText(text):
    # # Remove numeric and bullet list indicators
    # text = re.sub(r'^\s*\d+[\.\)]\s*', '', text, flags=re.MULTILINE)
    # text = re.sub(r'^\s*\*\s*', '', text, flags=re.MULTILINE)
    # # Remove punctuation at the end of each line
    # text = re.sub(r'\s*[.,;:!?]+\s*$', '', text, flags=re.MULTILINE)
    # # Remove extra whitespaces
    # text = re.sub(r'[ \t]+', ' ', text)
    
    # Do all of the above in one line for efficiency and performance of less re.sub calls
    text = re.sub(r'^\s*(\d+[\.\)]\s*|\*\s*)|[.,;:!?]+|\s+', ' ', text, flags=re.MULTILINE)
    return text.strip()

def cleanLines(text: list[str] | str):
    if isinstance(text, str):
        return [cleanText(line) for line in text.split('\n') if line.strip() != '']
    if isinstance(text, list):
        return [cleanText(line) for line in text if line.strip() != '']

def getNctIdsFromFolder(folder):
    try:
        return {file[:11] for file in os.listdir(folder) if file.startswith("NCT")}
    except Exception as e:
        logger.critical(f"Error accessing folder {folder}: {e}")
        return set() 
