"""
This file defines the pydantic models used in the logical structurization process to represent the logical structure between the atomic criteria extracted from the identification process.

All of the classes below which start with LLM are used as the output format for the LLM, the rest are how we end up storing the data internally.

Classes:
    LLMLogicalAnd: Represents a logical AND relationship between criteria.
    LLMLogicalOr: Represents a logical OR relationship between criteria.
    LLMLogicalNot: Represents a logical NOT operation on a criterion or logical expression.
    LLMLogicalXor: Represents a logical XOR relationship between criteria.
    LLmLogicalConditional: Represents a conditional (if then else) relationship between criteria.
    LLMLogicalWrapperResponse: Represents the response from the LLM with the logical structure.
    LogicalLine: Represents a line of eligibility criteria that has been logically structured.
    LogicalTrial: Represents a trial with logically structured criteria.

Notes:
    - If you change the docstring of the Pydantic models below, you will be changing the "prompt" to the LLMs since the descriptions are used when the LLM reads the output format. Add comments instead if needed.
    - The LogicalLine model includes both the identified line and its logical structure and is the core of our logical structurization process.
    - The LogicalTrial model includes lists of successfully structurized lines and lines that failed to be structurized and is the end result of our logical structurization process.
"""

from pydantic import BaseModel, Field
from typing import List, Union
from src.models.identified_criteria import IdentifiedLine, RawTrialData, LLMSingleRawCriterion

class LLMLogicalAnd(BaseModel):
    """
    Represents a logical AND relationship between criteria.
    """
    and_criteria: List[Union[LLMSingleRawCriterion, "LLMLogicalAnd", "LLMLogicalOr", "LLMLogicalNot","LLMLogicalXor", "LLmLogicalConditional" ]] = Field(..., description="The criteria involved in the relationship.")

class LLMLogicalOr(BaseModel):
    """
    Represents a logical OR relationship between criteria.
    """
    or_criteria: List[Union[LLMSingleRawCriterion, "LLMLogicalAnd", "LLMLogicalOr", "LLMLogicalNot","LLMLogicalXor", "LLmLogicalConditional" ]] = Field(..., description="The criteria involved in the relationship.")

class LLMLogicalNot(BaseModel):
    """
    Represents a logical NOT operation on a criterion or logical expression. Ensure that negation isn't already implicit in the criterion's value (e.g., 'must not be older than 18' is already represented by 'age ≤ 18 and no need for additional LLMLogicalNot').
    """
    not_criteria: Union[LLMSingleRawCriterion, "LLMLogicalAnd", "LLMLogicalOr", "LLMLogicalNot","LLMLogicalXor", "LLmLogicalConditional" ] = Field(..., description="The criteria involved in the relationship.")

class LLMLogicalXor(BaseModel):
    """
    Represents a logical XOR relationship between criteria.
    """
    xor_criteria: List[Union[LLMSingleRawCriterion, "LLMLogicalAnd", "LLMLogicalOr", "LLMLogicalNot","LLMLogicalXor", "LLmLogicalConditional" ]] = Field(..., description="The criteria involved in the relationship.")


class LLmLogicalConditional(BaseModel):
    """
    Represents a conditional relationship between criteria.
    """
    condition: Union[LLMSingleRawCriterion, "LLMLogicalAnd", "LLMLogicalOr", "LLMLogicalNot","LLMLogicalXor", "LLmLogicalConditional" ] = Field(..., description="The condition criterion (antecedent)")
    then_criteria: Union[LLMSingleRawCriterion, "LLMLogicalAnd", "LLMLogicalOr", "LLMLogicalNot","LLMLogicalXor", "LLmLogicalConditional" , None] = Field(..., description="The criteria that apply if the condition (antecedent) is met. (consequent)")
    else_criteria: Union[LLMSingleRawCriterion, "LLMLogicalAnd", "LLMLogicalOr", "LLMLogicalNot","LLMLogicalXor", "LLmLogicalConditional" , None] = Field(..., description="The criteria that apply if the condition (antecedent) is not met (optional consequent).")

LLMLogicalAnd.model_rebuild()
LLMLogicalOr.model_rebuild()
LLMLogicalNot.model_rebuild()
LLMLogicalXor.model_rebuild()
LLmLogicalConditional.model_rebuild()

#This is necessary because we can't tell the LLM to respond in one of the following types, instead we have to give it one type to respond in so this handles that constraint
class LLMLogicalWrapperResponse(BaseModel):
    """
    Represents the response from the LLM.
    """
    logicalRepresentation: Union[LLMLogicalAnd, LLMLogicalOr, LLMLogicalNot, LLMLogicalXor, LLmLogicalConditional] = Field(..., description="The logical representation of the criteria.")

class LogicalLine(BaseModel):
    """
    Represents a line of eligibility criteria that has been logically structured.
    """
    identified_line: IdentifiedLine = Field(..., description="The identified line this was made from.")
    logical_structure: Union[LLMSingleRawCriterion, LLMLogicalAnd, LLMLogicalOr, LLMLogicalNot, LLMLogicalXor, LLmLogicalConditional] = Field(..., description="The logically structured Criteria.")
    # Note that we won't add a validator here because we still want to be able to store the failed lines. as in we won't make use of a pydantic validator to check if the logical_structure actually includes all of the identified_line's criteria. Instead we will do that in our procedure which "logifies" the lines to save the failed lines.

class LogicalTrial(BaseModel):
    info: RawTrialData = Field(..., description="Raw data of the clinical trial.")
    inclusion_lines: List[LogicalLine] = Field(
        ..., description="List of inclusion lines successfully logically structurized."
    )
    exclusion_lines: List[LogicalLine] = Field(
        ..., description="List of exclusion lines successfully logically structurized."
    )
    miscellaneous_lines: List[LogicalLine] = Field(
        ..., description="List of miscellaneous lines successfully logically structurized."
    )
    failed_inclusion: List[LogicalLine] = Field(
        ...,description="List of inclusion lines that failed to be logically structurized."
    )
    failed_exclusion: List[LogicalLine] = Field(
        ...,description="List of exclusion lines that failed to be logically structurized."
    )
    failed_miscellaneous: List[LogicalLine] = Field(
        ...,description="List of miscellaneous lines that failed to be logically structurized."
    )