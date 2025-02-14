# models/structured_criteria.py

from pydantic import BaseModel, Field
from typing import List, Union
from enum import Enum

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


class Operator(str, Enum):
    """
    Represents an operator for comparison in criteria.
    """
    GREATER_THAN = ">"
    LESS_THAN = "<"
    EQUAL_TO = "="
    NOT_EQUAL_TO = "!="
    GREATER_THAN_OR_EQUAL_TO = ">="
    LESS_THAN_OR_EQUAL_TO = "<="

class Comparison(BaseModel):
    """
    Represents a comparison operation for a value.
    """
    operator: Operator = Field(..., description="The comparison operator.")
    value: Union[int, float] = Field(..., description="The value to compare against.")

class Range(BaseModel):
    """
    Represents a range for a value.
    """
    comparisons: List[Comparison] = Field(..., description="List of comparison operations defining the range.")

class SingleRawCriterion(BaseModel):
    """
    Represents an atomic criterion extracted from the eligibility criteria.
    This model captures the specific property/attribute being tested, what is asked about it (requirement_type), and the expected value.
    
    example:
        input:
        "Tissue from tumor must be available",
                
        output:
        "exact_snippets": [
            "Tissue from tumor must be available"
        ],
        "criterion": "tumor tissue",
        "requirement_type": "availability",
        "value": true
    """
    
    exact_snippets: List[str] = Field(
        ..., description="List of exact text snippets from the eligibility criteria that were used to extract this criterion."
    )
    
    criterion: str = Field(
        ..., description="The specific property, attribute, or condition that is being tested (e.g., 'age', 'lung cancer', 'BMI'). include the general version here and specify later in requirement_type (eg. white blood cell as criterion and count as attribute instead of white blood cell count as criterion) note that you can have the same criterion with different requirement types. (such as criterion tumor then different requirement types like presence, severity, quantity)"
    )
    
    requirement_type: str = Field(
        ..., description="what about the criterion is being tested (e.g presence, severity, quantity, N/A if it doesn't make sense for the criterion to have an attribute (eg. age))."
    )
    
    expected_value: Union[bool, int, float, str, Comparison, Range] = Field(
        ..., description="The expected value for the criterion. only use string if nothing else is applicable"
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

