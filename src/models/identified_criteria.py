# models/structured_criteria.py
"""
This file defines the pydantic models used to represent the structured atomic criteria extracted from the eligibility criteria of a clinical trial.
This is only the criteria, not the logical structure of the criteria.

All of the classes below which start with LLM are used as the output format for the LLM, the rest are how we end up storing the data internally.

Classes:
    RawTrialData: Represents the raw data of a clinical trial.
    LLMOperator: Enum representing comparison operators for numerical comparisons.
    LLMNumericalComparison: Represents a numerical comparison operation for an expected value.
    LLMRange: Represents a range via multiple LLMNumericalComparison objects.
    LLMSingleRawCriterion: Represents an atomic criterion extracted from the eligibility criteria.
    IdentifiedLine: Represents a structured line of eligibility criteria.
    IdentifiedTrial: Represents the collection of all structured atomic criteria and leftovers.
    LLMIdentifiedLineResponse: Represents the response from an LLM with extracted atomic criteria.

Notes:
    - If you change the docstring of the Pydantic models below, you will be changing the "prompt" to the LLMs since the descriptions are used when the LLM reads the output format. Add comments instead if needed.
    - The LLMSingleRawCriterion model captures the general property/attribute being tested, what is asked about it (requirement_type), and the expected value and is the core of our identification process.
    - The IdentifiedTrial model includes lists of successfully identified lines and lines that failed to be identified and is the end result of our identification process.
"""


from pydantic import BaseModel, Field
from typing import List, Union
from enum import Enum


#! if you change the docstring of the pydantic models below, you will be changing the "prompt" to the llms since the descriptions are used when the llm reads the output format. Add comments instead if needed

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

class LLMNumericalComparison(BaseModel):
    """
    Represents a numerical comparison operation for an expected value.
    """
    operator: LLMOperator = Field(..., description="The comparison operator.")
    value: Union[int, float] = Field(..., description="The value to compare against.")

class LLMRange(BaseModel):
    """
    Represents a range via multiple NumericalComparison objects to be used in expected value.
    """
    comparisons: List[LLMNumericalComparison] = Field(..., description="List of comparison operations defining the range.")


#TODO we should test out having this be a criterion and then list of requirement type and expected value pairs. this would better represent the data and enforce the idea that a criterion can have multiple requirement types and expected values associated with it to the llm better than putting that as text in the prompt. would still have to unwrap it when locally saving it in order to use it in the logical structurization process.

#TODO test out different examples, or at least an example which covers more edge cases

#TODO in far future test out not having the sample one shot in description, having few-shot, or if possible doing reinforcement fine tuning instead.
class LLMSingleRawCriterion(BaseModel):
    """
    Represents an atomic criterion extracted from the eligibility criteria.
    This model captures the general property/attribute being tested, what is asked about it (requirement_type), and the expected value.
    
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
        ..., description="The specific property, attribute, or condition that is being tested (e.g., 'age', 'lung cancer', 'BMI'). include the general version here and specify later in requirement_type (eg. white blood cell as criterion and count as attribute instead of white blood cell count as criterion). Note that you can have the same criterion with different requirement types. (such as criterion tumor then different requirement types like presence, severity, quantity)"
    )
    
    requirement_type: str = Field(
        ..., description="what about the criterion is being tested (e.g presence, severity, quantity, N/A if it doesn't make sense for the criterion to have an attribute (eg. age))."
    )
    
    expected_value: Union[bool, str, List[str], LLMNumericalComparison, LLMRange] = Field(
        ..., description="The expected value for the criterion. only use string if nothing else is applicable"
    )

class IdentifiedLine(BaseModel):
    """
    Represents a structured line of eligibility criteria.
    """
    line: str = Field(..., description="The original line of eligibility criteria.")
    criterions: List[LLMSingleRawCriterion] = Field(..., description="List of structured criteria.")
    
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
    atomic_criteria: List[LLMSingleRawCriterion] = Field(
        ..., description="List of all atomic criteria extracted from the trial."
    )