# repositories/trial_repository.py

"""
This module provides functions to save and load Pydantic models to and from JSON files.
Made this way so that in the future we can modify save and load to use a database instead of files without having to change any other code.

Functions:
    export_pydantic_to_json(model: BaseModel, file_name: str, folder: str) -> bool:
        Saves a Pydantic model to a JSON file.
    
    load_pydantic_from_json(folder: str, file_name: str, model_class: Type[T]) -> Optional[T]:
        Loads a Pydantic model from a JSON file.
"""

import os
import logging
import traceback
from typing import Optional, Type, TypeVar
from pydantic import BaseModel

# Configure logging
logger = logging.getLogger(__name__)


def export_pydantic_to_json(model: BaseModel, file_name: str, folder: str) -> bool:
    """
    Saves any Pydantic model to a JSON file.

    Args:
        model (BaseModel): The Pydantic model to save.
        file_name (str): The name of the file.
        folder (str): The folder to save the file in.

    Returns:
        bool: True if saved successfully, False otherwise.
    """
    
    try:
        os.makedirs(folder, exist_ok=True)
        file_path = os.path.join(folder, file_name)
        
        with open(file_path, 'w', encoding="utf-8") as f:
            #!IMPORTANT serialize_as_any=False is used to avoid the recursive/cyclic serialization error of the logical models
            # all of the relational operators can hold themselves as children, and pydantic doesn't like that
            f.write(model.model_dump_json(indent=4, serialize_as_any=False, warnings=False))
        logger.info("Model saved successfully at %s", file_path)
        return True
    except Exception as e:
        logger.error("Error saving model: %s", e)
        logger.error("Stack trace: %s", traceback.format_exc())
        return False

# necessary to make the loading generic and type agnostic
T = TypeVar('T', bound=BaseModel)

def load_pydantic_from_json(folder: str, file_name: str, model_class: Type[T]) -> Optional[T]:
    """
    Loads a Pydantic model from a JSON file.

    Args:
        folder (str): The folder where the file is located.
        file_name (str): The name of the file.
        model_class (Type[T]): The Pydantic model class.

    Returns:
        Optional[T]: The loaded model as a pydantic object or None if failed.
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