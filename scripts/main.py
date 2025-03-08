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


# Add project root to Python path to ensure imports work correctly
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from src.utils.config import setup_logging
from src.services.trial_manager import process_trial

# Configure application logging
setup_logging()

    
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

def get_trials() -> list[str] | None:
    """
    Present options to the user for selecting trials to process.
    
    Returns:
        list[str] | None: List of NCT IDs to process, or None if user chooses to quit.
    """
    while True:
        user_choice = input("Please choose one of the following\n'm' for manual input\n'a' to process all cancer trials from CHIA\n'q' to quit: ").strip().lower()

        if user_choice == 'm':
            return getTrialsFromUser()
        elif user_choice == 'a':
            return getChiaCancerTrials()
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
    
    # Process each trial
    for i, nct_id in enumerate(trials, 1):
        logger.info(f"Processing trial {i}/{len(trials)}: NCT ID {nct_id}")
        try:
            process_trial(nct_id)
            logger.info(f"Successfully processed trial {nct_id}")
        except Exception as e:
            logger.error(f"Failed to process trial {nct_id}: {str(e)}")
    
    logger.info("Processing complete")

if __name__ == "__main__":
    main()