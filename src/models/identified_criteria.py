# models/identified_criteria.py
"""
Data Models for Structured Clinical Trial Criteria

This module defines the Pydantic models used to represent structured atomic criteria
extracted from clinical trial eligibility criteria. These models represent the individual
criteria, not the logical relationships between them.

Classes prefixed with 'LLM' are used as output formats for LLM processing, while
other classes are used for internal data storage.

Classes:
    RawTrialData: Raw clinical trial data including eligibility criteria.
    LLMOperator: Enumeration of comparison operators.
    LLMNumericalComparison: Numerical comparison with operator and value.
    LLMRange: Range defined by multiple numerical comparisons.
    LLMSingleRawCriterion: Atomic criterion extracted from eligibility criteria.
    IdentifiedLine: Line of eligibility criteria with structured criteria.
    IdentifiedTrial: Collection of all structured atomic criteria for a trial.
    LLMIdentifiedLineResponse: LLM response format for identified criteria.

Important:
    The docstrings of Pydantic models are used as prompts for LLM processing.
    Changing these docstrings will alter how the LLM interprets the output format.
    Use code comments rather than docstring modifications if documentation changes
    are needed without affecting LLM behavior.
"""


from pydantic import BaseModel, Field
from typing import List, Union
from enum import Enum


class RawTrialData(BaseModel):
    """
    Represents the raw data of a clinical trial.
    """
    nct_id: str = Field(..., alias='nct_id', description="Clinical trial NCT ID.")
    official_title: str = Field(..., description="Official title of the clinical trial.")
    inclusion_criteria: str = Field(..., description="inclusion criteria of the clinical trial.")
    exclusion_criteria: str = Field(..., description="exclusion criteria of the clinical trial.")
    miscellaneous_criteria: str = Field(..., description="miscellaneous criteria of the clinical trial.")


class LLMOperator(str, Enum):
    """
    Represents an operator to be used in NumericalComparisons.
    """
    GREATER_THAN = ">"
    LESS_THAN = "<"
    EQUAL_TO = "="
    NOT_EQUAL_TO = "!="
    GREATER_THAN_OR_EQUAL_TO = ">="
    LESS_THAN_OR_EQUAL_TO = "<="
    
    def __eq__(self, value: object) -> bool:
        return str(self) == str(value)
    
    def __hash__(self) -> int:
        return hash(self.value)

class LLMNumericalComparison(BaseModel):
    """
    Represents a numerical comparison operation for an expected value.
    """
    operator: LLMOperator = Field(..., description="The comparison operator.")
    value: Union[int, float] = Field(..., description="The value to compare against.")
    unit: str = Field(..., description="The unit of the value being compared, if applicable, N/A otherwise.")
    
    def __eq__(self, value: object) -> bool:
        if isinstance(value, LLMNumericalComparison):
            return str(self) == str(value)
        return False
    
    def __hash__(self) -> int:
        return hash((self.operator, self.value, self.unit))

class LLMRange(BaseModel):
    """
    Represents a range via multiple NumericalComparison objects to be used in expected value.
    """
    comparisons: list[LLMNumericalComparison] = Field(..., description="List of comparison operations defining the range.")
    
    def __eq__(self, value: object) -> bool:
        if isinstance(value, LLMRange):
            return str(self) == str(value)
        return False
    
    def __hash__(self) -> int:
        return hash(tuple(self.comparisons))


# TODO: Consider restructuring to use a criterion with a list of requirement type 
# and expected value pairs. This would better represent the data structure and 
# reinforce to the LLM that a criterion can have multiple requirement types and
# expected values. Would need to unwrap this for logical structurization.

# TODO: Test different example sets, particularly examples covering edge cases.

# TODO: Consider alternatives to one-shot examples in the description:
# - Few-shot examples
# - Reinforcement fine-tuning for this specific task

class Requirement(BaseModel):
    """
    Represents a requirement type and its expected value for a criterion.
    """
    requirement_type: str = Field(
        ..., description="What about the criterion is being tested (e.g presence, severity, quantity, N/A if it doesn't make sense for the criterion to have an attribute (eg. age))."
    )
    expected_value: Union[bool, str, List[str], LLMNumericalComparison, LLMRange] = Field(
        ..., description="The expected value for the requirement. Only use string if nothing else is applicable."
    )
    
    def __eq__(self, other):
        if isinstance(other, Requirement):
            return str(self) == str(other)
        return False

    def __hash__(self):
        return hash((self.requirement_type, self.expected_value))

class LLMMultiRequirementCriterion(BaseModel):
    """
    Represents an atomic criterion extracted from the eligibility criteria.
    This model captures the general property/attribute being tested and a list of requirements with their expected values.
    
    example:
        input:
        "Tissue from tumor must be available and > 2 cm in diameter.",
                
        output:
        "exact_snippets": "Tissue from tumor must be available ... > 2 cm in diameter.",
        "criterion": "tumor tissue",
        "requirements": [
            {
                "requirement_type": "availability",
                "expected_value": true
            },
            {
                "requirement_type": "size",
                "expected_value": {
                    "operator": ">",
                    "value": 2,
                    "unit": "cm"
                }
            }
        ]
    """
    
    exact_snippets: str = Field(
        ..., description="Exact text snippets from the eligibility criteria that were used to extract this criterion, using ellipses (...) for non-consecutive text."
    )
    
    criterion: str = Field(
        ..., description="The specific property, attribute, or condition that is being tested (e.g., 'age', 'lung cancer', 'BMI')."
    )
    
    requirements: List[Requirement] = Field(
        ..., description="List of requirements and their expected values for the criterion."
    )

class IdentifiedLine(BaseModel):
    """
    Represents a structured line of eligibility criteria.
    """
    line: str = Field(..., description="The original line of eligibility criteria.")
    criterions: List[LLMMultiRequirementCriterion] = Field(..., description="List of structured criteria.")
    
class IdentifiedTrial(BaseModel):
    """
    Represents the collection of all structured atomic criteria and leftovers.
    """
    info: RawTrialData = Field(..., description="Raw data of the clinical trial.")
    inclusion_lines: List[IdentifiedLine] = Field(
        ..., description="List of inclusion lines successfully identified."
    )
    exclusion_lines: List[IdentifiedLine] = Field(
        ..., description="List of exclusion lines successfully identified."
    )
    miscellaneous_lines: List[IdentifiedLine] = Field(
        ..., description="List of miscellaneous lines successfully identified."
    )
    failed_inclusion: List[IdentifiedLine] = Field(
        ...,description="List of inclusion lines that failed to be identified."
    )
    failed_exclusion: List[IdentifiedLine] = Field(
        ...,description="List of exclusion lines that failed to be identified."
    )
    failed_miscellaneous: List[IdentifiedLine] = Field(
        ...,description="List of miscellaneous lines that failed to be identified."
    )

class LLMIdentifiedLineResponse(BaseModel):
    """
    Represents the collection of all structured atomic criteria and leftovers.
    """
    atomic_criteria: List[LLMMultiRequirementCriterion] = Field(
        ..., description="List of all atomic criteria extracted from the trial."
    )