# models/trial.py

from pydantic import BaseModel, Field
from typing import Optional, Union
from .criterion import AtomicCriterion, CompoundCriterion, Criterion, CategorizedCriterion, HierarchicalCriterion, NonsenseCriterion





class Trial(BaseModel):
    """
    Represents a clinical trial with structured criteria.
    """
    raw_data: RawTrialData = Field(..., description="Raw data of the clinical trial.")
    structurized: Optional[Union[AtomicCriterion, HierarchicalCriterion, CompoundCriterion, CategorizedCriterion, NonsenseCriterion]] = Field(
        None, description="Structured representation of the eligibility criteria."
    )
