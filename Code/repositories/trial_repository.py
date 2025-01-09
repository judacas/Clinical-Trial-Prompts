# repositories/trial_repository.py

import os
import logging
from typing import Optional
from models.structured_criteria import ParsedTrial
from models.trial import Trial

# Configure logging
logger = logging.getLogger(__name__)

def save_trial(trial: ParsedTrial, file_name: str, folder: str ) -> bool:
    """
    Saves the trial data to a JSON file.

    Args:
        trial (Trial): The trial to save.
        folder (str): The folder to save the file in.
        file_name (str): The name of the file.

    Returns:
        bool: True if saved successfully, False otherwise.
    """
    logger.info("Saving trial NCT ID: %s", trial.info.nct_id)
    folder = os.path.join(os.path.dirname(os.path.relpath(__file__)),folder)
    
    try:
        os.makedirs(folder, exist_ok=True)
        file_path = os.path.join(folder, file_name)
        with open(file_path, 'w', encoding="utf-8") as f:
            f.write(trial.model_dump_json(indent=4, serialize_as_any=True))
        logger.info("Trial saved successfully at %s", file_path)
        return True
    except Exception as e:
        logger.error("Error saving trial: %s", e)
        return False
    


def load_trial(folder: str, file_name: str) -> Optional[Trial]:
    """
    Loads the trial data from a JSON file.

    Args:
        folder (str): The folder where the file is located.
        file_name (str): The name of the file.

    Returns:
        Optional[Trial]: The loaded trial or None if failed.
    """
    logger.info("Loading trial from %s", os.path.join(folder, file_name))
    try:
        file_path = os.path.join(folder, file_name)
        with open(file_path, 'r', encoding="utf-8") as f:
            data = f.read()
            trial = Trial.model_validate_json(data)
        logger.info("Trial loaded successfully.")
        return trial
    except Exception as e:
        logger.error("Error loading trial: %s", e)
        return None
