# repositories/trial_repository.py

import os
import logging
from typing import Optional
<<<<<<< HEAD
=======
from models.structured_criteria import ParsedTrial
>>>>>>> 0fc8b9f9 (attempting to fix lost git history)
from models.trial import Trial

# Configure logging
logger = logging.getLogger(__name__)


<<<<<<< HEAD
def save_trial(trial: Trial, folder: str, file_name: str) -> bool:
=======
def save_trial(trial: ParsedTrial, folder: str, file_name: str) -> bool:
>>>>>>> 0fc8b9f9 (attempting to fix lost git history)
    """
    Saves the trial data to a JSON file.

    Args:
        trial (Trial): The trial to save.
        folder (str): The folder to save the file in.
        file_name (str): The name of the file.

    Returns:
        bool: True if saved successfully, False otherwise.
    """
<<<<<<< HEAD
    logger.info("Saving trial NCT ID: %s", trial.raw_data.nct_id)
=======
    logger.info("Saving trial NCT ID: %s", trial.info.nct_id)
>>>>>>> 0fc8b9f9 (attempting to fix lost git history)
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
