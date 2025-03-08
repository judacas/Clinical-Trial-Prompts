# repositories/trial_repository.py
"""
Trial Data Persistence Module

This module provides functions to save and load Pydantic models to and from JSON files.
It is designed with future extensibility in mind, so that storage mechanisms (e.g., file
system, database) can be changed without modifying client code.

Functions:
    export_pydantic_to_json: Serialize and save a Pydantic model to a JSON file.
    load_pydantic_from_json: Deserialize a Pydantic model from a JSON file.
"""

import os
import logging
import traceback
from typing import Optional, Type, TypeVar
from pydantic import BaseModel

# Configure logging
logger = logging.getLogger(__name__)

# Type variable for generic model types
T = TypeVar('T', bound=BaseModel)


def export_pydantic_to_json(model: BaseModel, file_name: str, folder: str) -> bool:
    """
    Saves a Pydantic model to a JSON file.

    Args:
        model (BaseModel): The Pydantic model to save.
        file_name (str): The name of the file to create.
        folder (str): The directory path where the file will be saved.

    Returns:
        bool: True if the model was saved successfully, False otherwise.
    """
    
    try:
        # Create the directory if it doesn't exist
        os.makedirs(folder, exist_ok=True)
        file_path = os.path.join(folder, file_name)
        
        # Write the model to the file
        with open(file_path, 'w', encoding="utf-8") as f:
            #! IMPORTANT: serialize_as_any=False prevents recursive/cyclic serialization errors
            f.write(model.model_dump_json(indent=4, serialize_as_any=False, warnings=False))
        
        logger.info("Model saved successfully at %s", file_path)
        return True
    
    except Exception as e:
        logger.error("Error saving model: %s", e)
        logger.error("Stack trace: %s", traceback.format_exc())
        return False


def load_pydantic_from_json(folder: str, file_name: str, model_class: Type[T]) -> Optional[T]:
    """
    Loads a Pydantic model from a JSON file.

    Args:
        folder (str): The directory path where the file is located.
        file_name (str): The name of the file to load.
        model_class (Type[T]): The Pydantic model class to deserialize into.

    Returns:
        Optional[T]: The deserialized Pydantic model instance, or None if loading failed.
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