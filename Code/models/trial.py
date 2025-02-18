# models/trial.py

from pydantic import BaseModel, Field
from typing import Optional, Union
from .criterion import AtomicCriterion, CompoundCriterion, CategorizedCriterion, HierarchicalCriterion, NonsenseCriterion
from Code.models.identified_criteria import RawTrialData





class Trial(BaseModel):
    """
    Represents a clinical trial with structured criteria.
    """
    raw_data: RawTrialData = Field(..., description="Raw data of the clinical trial.")
    structurized: Optional[Union[AtomicCriterion, HierarchicalCriterion, CompoundCriterion, CategorizedCriterion, NonsenseCriterion]] = Field(
        None, description="Structured representation of the eligibility criteria."
    )
