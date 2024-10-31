# models/trial.py

from pydantic import BaseModel, Field
from typing import Optional
from .criterion import Criterion, CategorizedCriterion


class RawTrialData(BaseModel):
    """
    Represents the raw data of a clinical trial.
    """
    nct_id: str = Field(..., alias='nct_id', description="Clinical trial NCT ID.")
    official_title: str = Field(..., description="Official title of the clinical trial.")
    criteria: Criterion = Field(..., description="Eligibility criteria of the trial.")


class Trial(BaseModel):
    """
    Represents a clinical trial with structured criteria.
    """
    raw_data: RawTrialData = Field(..., description="Raw data of the clinical trial.")
    structurized: Optional[CategorizedCriterion] = Field(
        None, description="Structured representation of the eligibility criteria."
    )
