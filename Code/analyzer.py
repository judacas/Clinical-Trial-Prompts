from fuzzywuzzy import fuzz
import glob
import os
import re
from colorama import Fore, Style
from tabulate import tabulate
import sympy
from errorManager import logError
from trial import Trial
import json

def read_chia_trial(nctId, ChiaFolder):
    chiaCriterias: list[str] = []
    for criteria_type in ['inc', 'exc']:
        file_path = os.path.join(ChiaFolder, nctId + f"_{criteria_type}.txt")
        try:
            with open(file_path, encoding='utf-8') as file:
                chiaCriterias += file.readlines()
        except FileNotFoundError as e:
            print(f"CHIA does not have an {criteria_type} criteria for {nctId}")
            logError(e=e, during=f"reading {criteria_type} criteria for {nctId}")
        except UnicodeDecodeError as e:
            logError(e=e, during=f"reading {criteria_type} criteria for {nctId}")
    return chiaCriterias

def read_personal_criteria(trial):
    personalCriteriaStr = trial.symPyExpression
    try:
        personalCriteriaExpression: sympy.Expr = sympy.sympify(personalCriteriaStr)
        return {str(crit) for crit in personalCriteriaExpression.free_symbols}
    except Exception:
        logError(e=Exception(f"Personal does not have a valid criteria for {trial.nctId}"), during=f"reading criteria for {trial.nctId}")
        return None
    

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
        chiaCriterias = read_chia_trial(trial.nctId, ChiaFolder)

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

def tokenize_lines(text:str):
    return [cleanText(line) for line in text.split('\n') if line.strip() != '']




def compare_lines(chia_lines, personal_lines, verbose=False, almostExactThreshold=95, goodEnoughThreshold=80):
    results, chiaFound = find_best_matches(personal_lines, chia_lines, goodEnoughThreshold)
    chiaLeft = [line for line in chia_lines if line not in chiaFound]
    chiaLeftoversFlipped, _ = find_best_matches(chiaLeft, personal_lines, goodEnoughThreshold)
    chiaLeftovers = [[row[1], row[0], row[2]] for row in chiaLeftoversFlipped]
    results += chiaLeftovers
    if verbose and len(results) > 0:
        print(tabulate(results, headers=['Personal', 'CHIA', 'Score'], tablefmt='fancy_grid', maxcolwidths=50))
        print("If we were to test it all as one we would get a score of", fuzz.ratio(' '.join(personal_lines), ' '.join(chia_lines)))
        print("the average score is", sum([int(row[2]) for row in results])/len(results))
    
    return results

def find_best_matches(source, destination, threshold):
    matches = []
    destinationsFound = []
    for item in source:
        best_match = max(destination, key=lambda x: fuzz.ratio(item, x))
        score = fuzz.ratio(item, best_match)
        
        if score >= threshold:
            destinationsFound.append(best_match)
            row = [color_text(str(cell), scoreToColor(score)) for cell in [item, best_match, score]]
        else:
            coloredSource = color_text(item, Fore.RED)
            coloredMatch = color_text(best_match, Fore.CYAN)
            coloredScore = color_text(str(score), Fore.RED)
            row = [coloredSource, coloredMatch, coloredScore]
        
        matches.append(row)
    return matches, destinationsFound


def scoreToColor(score, ALmostExactThreshold=95, GoodEnoughThreshold=80):
    if score > 100 or score < 0:
        raise ValueError(f"Invalid score: {score}, must be between 0 and 100")
    if score >= ALmostExactThreshold:
        return Fore.GREEN
    elif score >= GoodEnoughThreshold:
        return Fore.YELLOW
    else:
        return Fore.RED

def color_text(text:str, color:str, AlmostExactThreshold=95, GoodEnoughThreshold=80):
    if not isinstance(text, str):
        raise ValueError(f"Invalid text: {text}, must be a string")
    color_end = Style.RESET_ALL
    # For some reason coloring isn't working with tabulate so have to print something before the color or else it will interpret the color code as a number and then crash. 
    # Solution was to simply print an invisible character at the beginning, can't be whitespace or else it will be removed by tabulate
    coloredText: str = '\u200B' + color + text + color_end
    return coloredText


        

def checkCHIADeprecation(CHIALocation, MyLocation):
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
    differentCounter = 0
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
        
        print(f"\n\n{trial} comparison:")
        print(f"CHIA has {len(chiaLines)} lines while your personal folder has {len(myLines)} lines")
        # print("CHIA:" ,chiaString)
        # print("\n\n\nPersonal:", myString)
        compare_lines(chiaLines, myLines, verbose=True)
    print(f"\n\n{differentCounter} trials are different in CHIA and your personal folder")
    
    
    
    

    
    
    