# process_trial.py

import logging
from services.trial_manager import process_trial
from repositories.trial_repository import save_trial
from services.analyzer import check_accuracy
import os

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def main():
    # Prompt the user for an NCT ID
    nct_id = input("Enter the NCT ID of the trial you want to process: ").strip()
    logger.info("Processing trial NCT ID: %s", nct_id)
    if trial := process_trial(nct_id, verbose=True):
        file_name = f"{nct_id}_structured.json"
        output_folder = "output"

        if save_trial(trial, output_folder, file_name):
            logger.info("Trial saved successfully.")
            # Check approval
            check_accuracy(trial)
        else:
            logger.error("Failed to save trial.")
    else:
        logger.error("Failed to process trial NCT ID: %s", nct_id)

if __name__ == "__main__":
    main()
