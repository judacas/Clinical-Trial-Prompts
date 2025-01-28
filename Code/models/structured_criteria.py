# models/structured_criteria.py

from pydantic import BaseModel, Field
from typing import List

class RawTrialData(BaseModel):
    """
    Represents the raw data of a clinical trial.
    """
    nct_id: str = Field(..., alias='nct_id', description="Clinical trial NCT ID.")
    official_title: str = Field(..., description="Official title of the clinical trial.")
    criteria: str = Field(..., description="Eligibility criteria of the clinical trial.")

# class CompoundCriterion(BaseModel):
#     """
#     Represents a combination of two criteria.
#     """
#     criteria: List[SingleRawCriterion] = Field(..., description="List of criteria to be combined.")
#     combination_type: str = Field(..., description="Type of combination (AND/OR).")

# class HierarchicalCriterion(BaseModel):
#     """
#     Represents a hierarchical relationship between two criteria.
#     """
#     if_criterion: SingleRawCriterion = Field(..., description="The 'if' criterion.")
#     then_criterion: SingleRawCriterion = Field(..., description="The 'then' criterion.")

    
class SingleRawCriterion(BaseModel):
    """
    Represents an atomic criterion extracted from the eligibility criteria. This is a single specific property/attribute/condition.
    """
    exact_snippets: List[str] = Field(
        ..., description="List of exact snippets used to identify criterion"
    )
    criterion: str = Field(
        ..., description="the specific property/attribute/condition that is being tested for in the patient."
    )
    value: str = Field(
        ..., description="The value of the criterion they are looking for."
    )

class structuredLine(BaseModel):
    """
    Represents a structured line of eligibility criteria.
    """
    line: str = Field(..., description="The original line of eligibility criteria.")
    criterions: List[SingleRawCriterion] = Field(..., description="List of structured criteria.")
    
class ParsedTrial(BaseModel):
    """
    Represents the collection of all structured atomic criteria and leftovers.
    """
    info: RawTrialData = Field(..., description="Raw data of the clinical trial.")
    lines: List[structuredLine] = Field(
        ..., description="List of lines successfully structurized."
    )
    failed: List[structuredLine] = Field(
        ...,description="List of lines that failed to be structurized."
    )
    
