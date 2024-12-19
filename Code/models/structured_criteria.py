# models/structured_criteria.py

from pydantic import BaseModel, Field
from typing import List
from models.LLM_responses import SingleRawCriterion

class RawTrialData(BaseModel):
    """
    Represents the raw data of a clinical trial.
    """
    nct_id: str = Field(..., alias='nct_id', description="Clinical trial NCT ID.")
    official_title: str = Field(..., description="Official title of the clinical trial.")
    criteria: str = Field(..., description="Eligibility criteria of the clinical trial.")

class CompoundCriterion(BaseModel):
    """
    Represents a combination of two criteria.
    """
    criteria: List[SingleRawCriterion] = Field(..., description="List of criteria to be combined.")
    combination_type: str = Field(..., description="Type of combination (AND/OR).")

class HierarchicalCriterion(BaseModel):
    """
    Represents a hierarchical relationship between two criteria.
    """
    if_criterion: SingleRawCriterion = Field(..., description="The 'if' criterion.")
    then_criterion: SingleRawCriterion = Field(..., description="The 'then' criterion.")

class ParsedTrial(BaseModel):
    """
    Represents the collection of all structured atomic criteria and leftovers.
    """
    info: RawTrialData = Field(..., description="Raw data of the clinical trial.")
    atomic_criteria: List[SingleRawCriterion] = Field(
        ..., description="List of all atomic criteria extracted from the trial."
    )
    leftovers: List[str] = Field(
        default_factory=list, description="List of text segments between the criteria."
    )
