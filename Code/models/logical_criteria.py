from pydantic import BaseModel, Field
from typing import List, Union
from .identified_criteria import IdentifiedLine, IdentifiedTrial, RawTrialData, SingleRawCriterion

class LLMLogicalAnd(BaseModel):
    """
    Represents a logical AND relationship between criteria.
    """
    and_criteria: List[Union[SingleRawCriterion, "LLMLogicalAnd", "LLMLogicalOr", "LLMLogicalNot","LLMLogicalXor", "LLmLogicalConditional" ]] = Field(..., description="The criteria involved in the relationship.")

class LLMLogicalOr(BaseModel):
    """
    Represents a logical OR relationship between criteria.
    """
    or_criteria: List[Union[SingleRawCriterion, "LLMLogicalAnd", "LLMLogicalOr", "LLMLogicalNot","LLMLogicalXor", "LLmLogicalConditional" ]] = Field(..., description="The criteria involved in the relationship.")

class LLMLogicalNot(BaseModel):
    """
    Represents a logical NOT operation on a criterion or logical expression. Ensure that negation isn't already implicit in the criterion's value (e.g., 'must not be older than 18' is already represented by 'age ≤ 18').
    """
    not_criteria: Union[SingleRawCriterion, "LLMLogicalAnd", "LLMLogicalOr", "LLMLogicalNot","LLMLogicalXor", "LLmLogicalConditional" ] = Field(..., description="The criteria involved in the relationship.")

class LLMLogicalXor(BaseModel):
    """
    Represents a logical XOR relationship between criteria.
    """
    xor_criteria: List[Union[SingleRawCriterion, "LLMLogicalAnd", "LLMLogicalOr", "LLMLogicalNot","LLMLogicalXor", "LLmLogicalConditional" ]] = Field(..., description="The criteria involved in the relationship.")


class LLmLogicalConditional(BaseModel):
    """
    Represents a conditional relationship between criteria.
    """
    condition: Union[SingleRawCriterion, "LLMLogicalAnd", "LLMLogicalOr", "LLMLogicalNot","LLMLogicalXor", "LLmLogicalConditional" ] = Field(..., description="The condition criterion (e.g., 'radiation therapy within 6 months').")
    then_criteria: Union[SingleRawCriterion, "LLMLogicalAnd", "LLMLogicalOr", "LLMLogicalNot","LLMLogicalXor", "LLmLogicalConditional" , None] = Field(..., description="The criteria that apply if the condition is met (e.g., 'must have had chemotherapy').")
    else_criteria: Union[SingleRawCriterion, "LLMLogicalAnd", "LLMLogicalOr", "LLMLogicalNot","LLMLogicalXor", "LLmLogicalConditional" , None] = Field(..., description="The criteria that apply if the condition is not met (optional).")

LLMLogicalAnd.model_rebuild()
LLMLogicalOr.model_rebuild()
LLMLogicalNot.model_rebuild()
LLMLogicalXor.model_rebuild()
LLmLogicalConditional.model_rebuild()

class LogicalWrapperResponse(BaseModel):
    """
    Represents the response from the LLM.
    """
    logicalRepresentation: Union[LLMLogicalAnd, LLMLogicalOr, LLMLogicalNot, LLMLogicalXor, LLmLogicalConditional] = Field(..., description="The logical representation of the criteria.")
    
class LogicalLine(BaseModel):
    """
    Represents a line of eligibility criteria that has been logically structured.
    """
    identified_line: IdentifiedLine = Field(..., description="The identified line this was made from.")
    logical_structure: Union[SingleRawCriterion, LLMLogicalAnd, LLMLogicalOr, LLMLogicalNot, LLMLogicalXor, LLmLogicalConditional] = Field(..., description="The logically structured Criteria.")
    # Note that we won't add a validator here because we still want to be able to store the failed lines.

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