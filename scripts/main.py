# main.py
"""
Clinical Trial Processing Application

This module serves as the entry point for the clinical trial processing application.
It provides a command-line interface for selecting and processing clinical trials.

The application can:
1. Process trials specified manually by NCT ID
2. Process all cancer trials from the CHIA dataset
3. Exit the application

Each trial is processed to extract and structure its eligibility criteria.
"""
import logging
import os
import sys
from typing import Generator

from src.utils.helpers import curl_with_status_check


# Add project root to Python path to ensure imports work correctly
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from src.utils.config import DEFAULT_OUTPUT_DIR, setup_logging
from src.services.trial_manager import process_trial

# Configure application logging
setup_logging(log_to_file=True, log_level=logging.DEBUG)

    
def getChiaCancerTrials() -> list[str]:
    """
    Retrieve a list of all cancer trial NCT IDs from the CHIA dataset.
    
    Returns:
        list[str]: List of NCT IDs for cancer trials.
    """
    onlyCancerFolder = os.path.join("..", "Trials", "CHIA", "OnlyCancerTrials")
    return [
        file.split(".")[0]
        for file in os.listdir(onlyCancerFolder)
        if file.endswith(".json")
    ]
    
def getTrialsFromUser() -> list[str]:
    """
    Prompt the user to enter trial NCT IDs manually.
    
    Returns:
        list[str]: List of user-specified NCT IDs.
    """
    trials = []
    while nct_id := input("Enter the NCT ID of the trial you want to process (or press Enter to finish): ").strip():
        trials.append(nct_id)
    return trials

def getAllCancerTrials() -> Generator[str, None, None]:
    """
    Retrieve a generator of all cancer trial NCT IDs available in clinicaltrials.gov.
    
    Yields:
        str: NCT ID for a cancer trial.
    """
    url = "https://clinicaltrials.gov/api/v2/studies?query.cond=cancer&query.term=cancer&query.titles=Cancer&fields=NCTId&pageSize=1"
    response = curl_with_status_check(url)
    studies = response.get("studies", [])
    nextToken = response.get("nextPageToken", "")

    while True:
        for study in studies:
            yield study["protocolSection"]["identificationModule"]["nctId"]
        
        if not nextToken:
            break
        
        next_url = f"{url}&pageToken={nextToken}"
        response = curl_with_status_check(next_url)
        studies = response.get("studies", [])
        nextToken = response.get("nextPageToken", "")


def get_trials() -> list[str] | Generator[str] | None:
    """
    Present options to the user for selecting trials to process.
    
    Returns:
        list[str] | None: List of NCT IDs to process, or None if user chooses to quit.
    """
    while True:
        user_choice = input("Please choose one of the following\n'm' for manual input\n'c' to process all cancer trials from CHIA\n'a' for all cancer trials\n'q' to quit: ").strip().lower()

        if user_choice == 'm':
            return getTrialsFromUser()
        elif user_choice == 'c':
            return getChiaCancerTrials()
        elif user_choice == 'a':
            return getAllCancerTrials()
        elif user_choice == 'q':
            return None
        else:
            print("Invalid choice. Please try again.")

def main():
    """
    Main application function. Handles user interaction and processes selected trials.
    """
    logger = logging.getLogger(__name__)
    logger.info("Application started...")
    
    trials = get_trials()
    if not trials:
        logger.info("No trials selected, exiting...")
        return
    
    if isinstance(trials, list):
        
        logger.info(f"Selected {len(trials)} trials for processing")
        logger.info("these are the trials selected: %s", trials)
    
    
    # Process each trial
    for i, nct_id in enumerate(trials, 1):
        if isinstance(trials, Generator):
            logger.info(f"Processing trial {i}: NCT ID {nct_id}")
        else:
            logger.info(f"Processing trial {i}/{len(trials)}: NCT ID {nct_id}")
        try:
            process_trial(nct_id, os.path.join(DEFAULT_OUTPUT_DIR, "allTrials"))
            logger.info(f"Successfully processed trial {nct_id}")
        except Exception as e:
            logger.error(f"Failed to process trial {nct_id}: {str(e)}")
    
    logger.info("Processing complete")

if __name__ == "__main__":
    main()