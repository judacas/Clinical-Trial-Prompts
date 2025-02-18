# repositories/trial_repository.py

import os
import logging
from typing import Optional, Type, TypeVar

from pydantic import BaseModel
from models.identified_criteria import IdentifiedTrial

# Configure logging
logger = logging.getLogger(__name__)

def save_trial(trial: IdentifiedTrial, file_name: str, folder: str ) -> bool:
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
    
T = TypeVar('T', bound=BaseModel)

def load_pydantic_model(folder: str, file_name: str, model_class: Type[T]) -> Optional[T]:
    """
    Loads a Pydantic model from a JSON file.

    Args:
        folder (str): The folder where the file is located.
        file_name (str): The name of the file.
        model_class (Type[T]): The Pydantic model class.

    Returns:
        Optional[T]: The loaded model or None if failed.
    """
    logger.info("Loading model from %s", os.path.join(folder, file_name))
    try:
        file_path = os.path.join(folder, file_name)
        with open(file_path, 'r', encoding="utf-8") as f:
            data = f.read()
            model = model_class.model_validate_json(data)
        logger.info("Model loaded successfully.")
        return model
    except Exception as e:
        logger.error("Error loading model: %s", e)
        return None
