import glob
import os
from colorama import Fore, Style
from tabulate import tabulate
import sympy
from errorManager import logError
from trial import Trial

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

    
    
    