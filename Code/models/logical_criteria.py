from pydantic import BaseModel, Field
from typing import List, Union
from .identified_criteria import SingleRawCriterion

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
class LogicalWrapperResponse(BaseModel):
    """
    Represents the response from the LLM.
    """
    logicalRepresentation: Union[LLMLogicalAnd, LLMLogicalOr, LLMLogicalNot, LLMLogicalXor, LLmLogicalConditional] = Field(..., description="The logical representation of the criteria.")
    
class LogicallyStructuredLine(BaseModel):
    """
    Represents a line of eligibility criteria that has been logically structured.
    """
    text: str = Field(..., description="The text of the line.")
    criteria: Union[SingleRawCriterion, LLMLogicalAnd, LLMLogicalOr, LLMLogicalNot, LLMLogicalXor, LLmLogicalConditional] = Field(..., description="The structured criteria.")
    
