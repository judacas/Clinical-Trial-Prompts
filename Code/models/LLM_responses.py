# models/structured_criteria.py

from pydantic import BaseModel, Field
from typing import List

class SingleRawCriterion(BaseModel):
    """
    Represents an atomic criterion extracted from the eligibility criteria.
    """
    raw_text: str = Field(
        ..., description="Exact substring from the original text representing the criterion."
    )
    paraphrased_text: str = Field(
        ..., description="Paraphrased version of the criterion for clarity."
    )
    
class oneParsedLine(BaseModel):
    """
    Represents the collection of all structured atomic criteria and leftovers.
    """
    atomic_criteria: List[SingleRawCriterion] = Field(
        ..., description="List of all atomic criteria extracted from the trial."
    )