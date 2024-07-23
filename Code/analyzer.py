from typing import Any
from fuzzywuzzy import fuzz
import glob
import os
import re
from colorama import Fore, Style
from loguru import logger
from tabulate import tabulate
import sympy
from myWrappers import deprecated
from trial import Trial
import json


def updatedCompareToChia(ChiaFolder, personalFolder, isProcessed):
    trialIds = getNctIdsFromFolder(personalFolder)
    validTrials = []
    inValidTrials = []
    unReadableTrials = []
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
        chiaCriteria = tokenize_lines(chiaCriteria)
        personalCriteria = tokenize_lines(personalCriteria)
        matches, leftOvers = updatedCompareLists(chiaCriteria, personalCriteria, 90)
        if not matches.count(""):
            validTrials.append(trial)
        else:
            inValidTrials.append(trial)
        printResults(trial, chiaCriteria, matches, list(leftOvers), personalFolder)
    resultsSummary = comparisonSummaryToString(len(trialIds), len(unReadableTrials), validTrials, inValidTrials)
    print("\n",json.dumps(resultsSummary, indent=4))
    with open (os.path.join(personalFolder, "comparisonSummary.json"), 'w', encoding='utf-8') as file:
        json.dump(resultsSummary, file, indent=4)
    
def comparisonSummaryToString(totalTrialNum, unReadableTrials, validTrials, inValidTrials) -> dict[str, Any]:
    return {
        "Summary": {
            "Total Trials Analyzed": totalTrialNum,
            "Trials Unable to Test": unReadableTrials,
            "Trials with Perfect Matches": len(validTrials),
            "Trials without Perfect Matches": len(inValidTrials)
        },
        "ValidTrials": validTrials,
        "InvalidTrials": inValidTrials
    }

def printResults(nctID, source: list[str], matches: list[str], leftOvers: list[str], folder=None):
    totalNotFound = matches.count("")
    totalFound = len(matches) - totalNotFound
    output = [
        f"\n\n{nctID} comparison:",
        "\nSummary:",
        f"CHIA has {len(source)} criteria while your personal folder has {len(matches)} criteria",
        f"Total found criteria: {totalFound}/{len(source)}",
        f"Total not Found: {totalNotFound}/{len(source)}",
        f"Total Extra: {len(leftOvers)}",
        f"This trial is {'VALID' if totalNotFound == 0 else 'INVALID'}"
    ]
    for table in matchingResultsToTables(source, matches, leftOvers):
        output.extend(("\n\n", table))
    output_str = '\n'.join(output)

    if folder:
        filePath = os.path.join(folder, f"{nctID}_comparison.txt")
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


def getChiaCriteriaAsList(ChiaFolder, nctId = None) -> list[str]:
    chiaCriterias: list[str] = []
    if nctId is None:
        raise ValueError("nctId must be specified")
    for criteria_type in ['inc', 'exc']:
        file_path = os.path.join(ChiaFolder, f"{nctId}_{criteria_type}.txt")
        try:
            with open(file_path, encoding='utf-8') as file:
                chiaCriterias.extend(tokenize_lines(file.read()))
        except FileNotFoundError:
            print(f"CHIA does not have an {criteria_type} criteria for {nctId}")
            logger.warning(f"reading {criteria_type} criteria for {nctId}")
        except UnicodeDecodeError:
            logger.warning(f"reading {criteria_type} criteria for {nctId}")
    return chiaCriterias

def getAllChiaCriteriasAsInFolder(ChiaFolder) -> dict[str, list[str]]:
    chiaCriterias = {}
    for fileName in set(glob.glob(os.path.join(ChiaFolder, "*.txt"))):
        nctId = os.path.basename(fileName)[:11]
        if criteria := getChiaCriteriaAsList(ChiaFolder, nctId):
            chiaCriterias[nctId] = tokenize_lines(criteria)
    return chiaCriterias

def getAllProcessedTrialsInFolder(folder) -> dict[str, list[str]]:
    trials: dict[str, list[str]] = {}
    for fileName in glob.glob(os.path.join(folder, "*_Processed.json")):
        nctId = os.path.basename(fileName)[:11]
        if criteria := getProcessedTrial(folder, nctId):
            trials[nctId] = tokenize_lines(criteria)
    return trials
def getAllRawTrialInFolder(folder) -> dict[str, list[str]]:
    trials: dict[str, list[str]] = {}
    for file in glob.glob(os.path.join(folder, "*.json")):
        nctId = os.path.basename(file)[:11]
        if criteria := getRawTrialInFolder(folder, nctId):
            trials[nctId] = tokenize_lines(criteria)
    return trials

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
    return tokenize_lines(criteria)

def getProcessedTrial(folder, nctId = None) -> list[str]:
    if nctId is None:
        raise ValueError("nctId must be specified")
    filePath = os.path.join(folder, f"{nctId}_Processed.json")
    try:
        with open(filePath, encoding='utf-8') as file:
            trialJSON = json.load(file)
            trial = Trial(serializedJSON=trialJSON)
            return sympyExpressionStringToCriteriaList(trial.symPyExpression)
    except FileNotFoundError:
        print(f"Could not find processed trial for {nctId}")
        logger.warning(f"reading processed trial for {nctId}")
    except Exception:
        print(f"Could not read processed trial for {nctId}")
        logger.warning(f"reading processed trial for {nctId}")
    return []
    
    

def sympyExpressionStringToCriteriaList(expressionString) -> list[str]:
    personalCriteriaExpression: sympy.Expr = sympy.sympify(expressionString)
    return tokenize_lines([str(crit) for crit in personalCriteriaExpression.free_symbols])

def read_personal_criteria(trial):
    personalCriteriaStr = trial.symPyExpression
    try:
        personalCriteriaExpression: sympy.Expr = sympy.sympify(personalCriteriaStr)
        return {str(crit) for crit in personalCriteriaExpression.free_symbols}
    except Exception:
        logger.error(f"Personal does not have a valid criteria for {trial.nctId}")
        return None
    
def testReaders(chiaFolder, personalFolder):
    chiaCriterias = getAllChiaCriteriasAsInFolder(chiaFolder)
    personalCriterias = getAllRawTrialInFolder(personalFolder)
    print("CHIA has the following criterias:")
    for nctId, criteria in chiaCriterias.items():
        print(nctId, criteria)
    print("\n")
    print("Personal has the following criterias:")
    for nctId, criteria in personalCriterias.items():
        print(nctId, criteria)

@deprecated
def write_comparison_to_file(nctId, matching_criteria, folder):
    # Prepare data for tabulate
    table_data = []
    for crit, match in matching_criteria.items():
        table_data.append([crit, match])

    # Create the plain text table
    table = tabulate(table_data, headers=['Personal Criteria', 'CHIA Criteria'], tablefmt='fancy_grid',maxcolwidths=50)

    # Write the table to a text file
    with open(os.path.join(folder, f"{nctId}_comparison.txt"), 'w', encoding='utf-8') as f:
        f.write(table)

@deprecated
def compareToChia (ChiaFolder, personalFolder):
    processedJSONs = glob.glob(os.path.join(personalFolder, "*_Processed.json"))
    trials: set[Trial] = {Trial(serializedJSON=file) for file in processedJSONs}
    chiaIDs = {os.path.basename(file)[:11] for file in glob.glob(os.path.join(ChiaFolder, "*.txt"))}
    
    nonChiaTrials = [trial.nctId for trial in trials if trial.nctId not in chiaIDs]
    
    trials = {trial for trial in trials if trial.nctId not in nonChiaTrials}
    print("\n\nThe following trials have a valid CHIA counterpart and will be compared:")
    for trial in trials:
        print(trial.nctId)
    print("\n")
    ChiaFailures = []
    personalFailures = []
    personalCritCounter = 0
    chiaCritCounter = 0
    matchingCritCounter = 0
    for trial in trials:
        print(f"Comparing {trial.nctId}...")
        chiaCriterias = getChiaCriteriaAsList(trial.nctId, ChiaFolder)

        if len(chiaCriterias) == 0:
            print(f"could not read CHIA criteria for {trial.nctId}, skipping...")
            ChiaFailures.append(trial.nctId)
            continue
            
        personalCriterias = read_personal_criteria(trial)
        if personalCriterias is None:
            print(f"could not read personal criteria for {trial.nctId}, skipping...")
            personalFailures.append(trial.nctId)
            continue
        personalCritCounter += len(personalCriterias)
        chiaCritCounter += len(chiaCriterias)
        matching_criteria = {crit: "No Match" for crit in personalCriterias}

        # Check each personal criteria against each CHIA criteria
        for personal_crit in personalCriterias:
            for chia_crit in chiaCriterias:
                if personal_crit in chia_crit:
                    matching_criteria[personal_crit] = chia_crit
                    matchingCritCounter += 1
                    break  # Stop checking other CHIA criteria once a match is found

        # Prepare data for tabulate
        table_data = []
        for crit, match in matching_criteria.items():
            if match == "No Match":
                coloredCrit = Fore.RED + crit
                coloredMatch = Fore.RED + match
            else:
                coloredCrit = Fore.GREEN + crit
                coloredMatch = Fore.GREEN +match
            table_data.append([coloredCrit, coloredMatch])

        # Print the matching criteria in a table
        print(tabulate(table_data, headers=['Personal Criteria', 'CHIA Criteria'], maxcolwidths=50, tablefmt='fancy_grid'))
        print(Style.RESET_ALL)
        write_comparison_to_file(trial.nctId, matching_criteria, personalFolder)
        
    print("\n\nThe following trials could not be compared:\n")
    print("Not part of chia:")
    for trial in nonChiaTrials:
        print("\t",trial)
    print("\nChia file unreadable:")
    for trial in ChiaFailures:
        print("\t",trial)
    print("\nPersonal file unreadable:")
    for trial in personalFailures:
        print("\t",trial)
    
    summary_data = [
        ["Total personal criteria", personalCritCounter],
        ["Total CHIA criteria", chiaCritCounter],
        ["personal - CHIA", personalCritCounter - chiaCritCounter],
        ["Total matching criteria", matchingCritCounter],
        ["Percentage of personal criteria that matched a CHIA criteria", f"{(matchingCritCounter/personalCritCounter*100):.2f}%"]
    ]
    
    print("\n\nSummary:")
    print(tabulate(summary_data, headers=['Statistic', 'Value'], tablefmt='fancy_grid', maxcolwidths=50))
    
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
    text.strip()
    # Remove numeric and bullet list indicators
    text = re.sub(r'^\s*\d+[\.\)]\s*', '', text, flags=re.MULTILINE)
    text = re.sub(r'^\s*\*\s*', '', text, flags=re.MULTILINE)
    # Remove punctuation at the end of each line
    text = re.sub(r'\s*[.,;:!?]+\s*$', '', text, flags=re.MULTILINE)
    # Remove extra whitespaces
    text = re.sub(r'[ \t]+', ' ', text)
    return text.strip()

def tokenize_lines(text: list[str] | str):
    if isinstance(text, str):
        return [cleanText(line) for line in text.split('\n') if line.strip() != '']
    if isinstance(text, list):
        return [cleanText(line) for line in text if line.strip() != '']
    else:
        raise ValueError("text must be a string or a list of strings")

@deprecated
def stripColors(table: list[list[str]]):
    #regex to remove both color codes and the reset sequence, yes I know I probably should've just not added them in the first place but too late for that now
    return [[re.sub(r'\u200b\x1b\[\d+m|\x1b\[0m', '', cell) for cell in row] for row in table]


@deprecated
def compare_lines(chia_lines, personal_lines, verbose=False, almostExactThreshold=95, goodEnoughThreshold=80):
    personalMatch, chiaFound = find_best_matches(personal_lines, chia_lines, almostExactThreshold, goodEnoughThreshold)
    chiaLeft = [line for line in chia_lines if line not in chiaFound]
    chiaLeftoversFlipped, _ = find_best_matches(chiaLeft, personal_lines,almostExactThreshold, goodEnoughThreshold)
    chiaLeftovers = [[row[1], row[0], row[2]] for row in chiaLeftoversFlipped]
    results = personalMatch + chiaLeftovers
    # Should I have just made it clear and found a way to add the colors when printed instead of removing them here?
    # Probably, but too late now :)
    # NOTE: need to remove colors in order to properly get score for stats later and also  to save to file since color only works for console/terminal
    clearResults = stripColors(results)
    if verbose and len(results) > 0:
        print(tabulate(results, headers=['Personal', 'CHIA', 'Score'], tablefmt='fancy_grid', maxcolwidths=50))
        print("If we were to test it all as one we would get a score of", fuzz.ratio(' '.join(personal_lines), ' '.join(chia_lines)))
        print("the average score is", sum([int(row[2]) for row in clearResults])/len(clearResults))
    
    return sorted(clearResults, key=lambda x: x[2]), sorted(stripColors(personalMatch), key=lambda x: x[2]), sorted(stripColors(chiaLeftovers), key=lambda x: x[2])

@deprecated
def find_best_matches(source, destination, almostExactThreshold, goodEnoughThreshold):
    matches = []
    destinationsFound = []
    for item in source:
        best_match = max(destination, key=lambda x: fuzz.ratio(item, x))
        score = fuzz.ratio(item, best_match)
        
        if score >= goodEnoughThreshold:
            destinationsFound.append(best_match)
            row = [color_text(str(cell), scoreToColor(score, almostExactThreshold, goodEnoughThreshold)) for cell in [item, best_match, score]]
        else:
            coloredSource = color_text(item, Fore.RED)
            coloredMatch = color_text(best_match, Fore.CYAN)
            coloredScore = color_text(str(score), Fore.RED)
            row = [coloredSource, coloredMatch, coloredScore]
        
        matches.append(row)
    return matches, destinationsFound

@deprecated
def scoreToColor(score, almostExactThreshold, goodEnoughThreshold):
    if score > 100 or score < 0:
        raise ValueError(f"Invalid score: {score}, must be between 0 and 100")
    if score >= almostExactThreshold:
        return Fore.GREEN
    elif score >= goodEnoughThreshold:
        return Fore.YELLOW
    else:
        return Fore.RED

@deprecated
def color_text(text:str, color:str, AlmostExactThreshold=95, GoodEnoughThreshold=80):
    if not isinstance(text, str):
        raise ValueError(f"Invalid text: {text}, must be a string")
    color_end = Style.RESET_ALL
    # For some reason coloring isn't working with tabulate so have to print something before the color or else it will interpret the color code as a number and then crash. 
    # Solution was to simply print an invisible character at the beginning, can't be whitespace or else it will be removed by tabulate
    coloredText: str = '\u200B' + color + text + color_end
    return coloredText


def getNctIdsFromFolder(folder):
    """
    Extracts NCT IDs from filenames in the specified folder.

    Args:
        folder (str): The path to the folder containing the files.

    Returns:
        set: A set of unique NCT IDs extracted from the filenames.
    """
    try:
        return {file[:11] for file in os.listdir(folder) if file.startswith("NCT")}
    except Exception as e:
        print(f"Error accessing folder {folder}: {e}")
        return set() 

@deprecated
def checkCHIADeprecation(CHIALocation, MyLocation):
    verbose = True
    almostExactThreshold = 95
    goodEnoughThreshold = 85
    chiaIDs = {os.path.basename(file)[:11] for file in glob.glob(os.path.join(CHIALocation, "*.txt"))}
    myIDs = {os.path.basename(file)[:11] for file in glob.glob(os.path.join(MyLocation, "*.json"))}
    deprecated = chiaIDs - myIDs
    if deprecated:
        print("\n\nThe following trials are in CHIA but not in your personal folder:")
        for trial in deprecated:
            print(trial)
    else:
        print("\n\nThere are no deprecated trials in CHIA")
    inPersonalButNotInCHIA = myIDs - chiaIDs
    if inPersonalButNotInCHIA:
        print("\n\nThe following trials are in your personal folder but not in CHIA:")
        for trial in inPersonalButNotInCHIA:
            print(trial)
    else:
        print("\n\nThere are no trials in your personal folder that are not in CHIA")
    print(len(deprecated), "trials are deprecated")
    print(len(myIDs), "trials are in your personal folder")
    print(len(chiaIDs), "trials are in CHIA")
    
    useful = myIDs & chiaIDs
    print(len(useful), "trials are in both CHIA and your personal folder which we will use for the following comparison:")
    invalidTrials = []
    validTrials = []
    for trial in useful:
        ChiaIncFile = os.path.join(CHIALocation, trial + "_inc.txt")
        ChiaExcFile = os.path.join(CHIALocation, trial + "_exc.txt")
        chiaString = ""
        if os.path.exists(ChiaIncFile):
            with open(ChiaIncFile, encoding='utf-8') as file:
                chiaString += file.read()
        if os.path.exists(ChiaExcFile):
            with open(ChiaExcFile, encoding='utf-8') as file:
                chiaString += file.read()
                
        myFile = os.path.join(MyLocation, trial + ".json")
        with open(myFile, encoding='utf-8') as file:
            myJSON = json.load(file)
            myString = myJSON.get("inclusionCriteria","") + "\n" + myJSON.get("exclusionCriteria","") + myJSON.get("Criteria","")
        
        chiaLines = tokenize_lines(chiaString)
        myLines = tokenize_lines(myString)
        
        if verbose:
            print(f"\n\n{trial} comparison:")
            print(f"CHIA has {len(chiaLines)} lines while your personal folder has {len(myLines)} lines")
        # print("CHIA:" ,chiaString)
        # print("\n\n\nPersonal:", myString)
        totalResults, personalResults, chiaResults = compare_lines(chiaLines, myLines, verbose, almostExactThreshold, goodEnoughThreshold)
        totalLevenshteinRatio = fuzz.ratio(' '.join(myLines), ' '.join(chiaLines))
        averageLevenshteinRatio = sum([int(row[2]) for row in totalResults])/len(totalResults)
        overAllRatio = (totalLevenshteinRatio + averageLevenshteinRatio)/2
        trialSummary = [trial, totalLevenshteinRatio, averageLevenshteinRatio, overAllRatio]
        if overAllRatio >= goodEnoughThreshold:
            validTrials.append(trialSummary)
        else:
            invalidTrials.append(trialSummary)
        
        with open(os.path.join(MyLocation, trial + "_comparison.txt"), 'w', encoding='utf-8') as f:
            if overAllRatio >= goodEnoughThreshold:
                f.write("VALID TRIAL\n")
            else:
                f.write("INVALID TRIAL\n")
            
            totalFound = [row for row in totalResults if int(row[2]) >= goodEnoughThreshold]
            if len(totalFound) > 0:
                f.write("Both CHIA and your personal trial have the following criteria:\n")
                f.write(tabulate(totalFound, headers=['Personal Criteria', 'CHIA Criteria', 'Score'], tablefmt='fancy_grid', maxcolwidths=50,))
                f.write("\n\n")
            else:
                f.write("CHIA and your personal trial have no criteria in common\n\n")
            
            onlyPersonal = [row for row in personalResults if int(row[2]) < goodEnoughThreshold]
            if len(onlyPersonal) > 0:
                f.write("Only your personal trial has the following criteria:\n")
                f.write(tabulate(onlyPersonal, headers=['Personal Criteria', 'CHIA Criteria', 'Score'], tablefmt='fancy_grid', maxcolwidths=50,))
                f.write("\n\n")
            else:
                f.write("Your personal trial has no unique criteria\n\n")
            
            if len(chiaResults) > 0:
                f.write("Only CHIA has the following criteria:\n")
                f.write(tabulate(chiaResults, headers=['Personal Criteria', 'CHIA Criteria', 'Score'], tablefmt='fancy_grid', maxcolwidths=50,))
                f.write("\n\n")
            else:
                f.write("CHIA has no unique criteria\n\n")
            
            f.write(f"Levenshtein Ratio of Entire trial at once: {totalLevenshteinRatio}\n")
            f.write(f"Average Levenshtein Ratio of individual lines: {averageLevenshteinRatio}\n")
            f.write(f"OverAll Ratio: {overAllRatio}\n")
    
    print(f"\n\nThe {len(validTrials)} trials Below all have an overAllRatio of {goodEnoughThreshold} or higher and will be kept")
    print(tabulate(sorted(validTrials, key=lambda x: x[3]), headers=['Trial', 'Total Ratio', 'Average Ratio', 'OverAll Ratio'], tablefmt='fancy_grid', maxcolwidths=50)) # type: ignore
    print(f"\n\nThe {len(invalidTrials)} trials below have an overAllRatio of less than {goodEnoughThreshold} and will be removed")
    print(tabulate(sorted(invalidTrials, key=lambda x: x[3]), headers=['Trial', 'Total Ratio', 'Average Ratio', 'OverAll Ratio'], tablefmt='fancy_grid', maxcolwidths=50)) # type: ignore

    
    
    
    

    
    
    