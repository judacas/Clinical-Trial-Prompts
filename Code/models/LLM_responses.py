# models/structured_criteria.py

from pydantic import BaseModel, Field
from typing import List
from models.structured_criteria import SingleRawCriterion


    
class oneParsedLine(BaseModel):
    """
    Represents the collection of all structured atomic criteria and leftovers.
    """
    atomic_criteria: List[SingleRawCriterion] = Field(
        ..., description="List of all atomic criteria extracted from the trial."
    )