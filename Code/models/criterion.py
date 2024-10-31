# models/criterion.py

from enum import Enum
from pydantic import BaseModel, Field
from typing import List, Optional, Sequence


class Category(str, Enum):
    """
    Enum representing the category of a criterion.
    """
    ATOMIC_CRITERION = "atomic_Criterion"
    COMPOUND_CRITERION = "compound_Criterion"
    HIERARCHICAL_CRITERION = "hierarchical_criterion"


class Criterion(BaseModel):
    """
    Base class representing a clinical trial criterion.
    """
    raw_text: str = Field(..., description="The raw text of the criterion.")


class CategorizedCriterion(Criterion):
    """
    Represents a criterion that has been categorized.
    """
    category: Category = Field(..., description="The category of the criterion.")
    category_reasoning: str = Field(..., description="Reasoning behind the categorization.")
    overall_thoughts: str = Field(..., description="Overall thoughts on the criterion.")

    def get_children(self) -> List['Criterion']:
        """
        Returns a list of child criteria.
        """
        return []


class Target(BaseModel):
    """
    Represents the target of an atomic criterion.
    """
    answer: str = Field(..., description="An answer considered true regarding the term.")
    dependent_criterion: Optional[Criterion] = Field(
        ..., description="Additional criteria that apply if this answer is true."
    )


class AtomicCriterion(CategorizedCriterion):
    """
    Represents an atomic criterion that cannot be broken down further.
    """
    root_term: str = Field(..., description="The root term without qualifiers.")
    qualifiers: List[str] = Field(..., description="Qualifiers that specify the criterion.")
    relation_type: str = Field(..., description="Relationship between the root term and the target.")
    target: List[Target] = Field(..., description="Targets for which the criterion is true.")
    additional_information: List[str] = Field(..., description="Additional context for the criterion")

    # def get_children(self) -> List['Criterion']:
    #     return []


class HierarchicalCriterion(CategorizedCriterion):
    """
    Represents a hierarchical criterion with parent and child criteria.
    """
    parent_criterion: Criterion = Field(..., description="The parent criterion.")
    child_criterion: Criterion = Field(..., description="The child criterion modifying the parent.")
    additional_information: List[str] = Field(
        ..., description="Additional context for the criterion."
    )

    def get_children(self) -> List['Criterion']:
        return [self.parent_criterion, self.child_criterion]


class LogicalOperator(str, Enum):
    """
    Enum representing logical operators.
    """
    AND = "AND"
    OR = "OR"


class CompoundCriterion(CategorizedCriterion):
    """
    Represents a compound criterion composed of multiple criteria.
    """
    logical_operator: LogicalOperator = Field(
        ..., description="Logical operator joining the criteria."
    )
    criterions: Sequence[Criterion] = Field(
        ..., description="List of criteria in the compound criterion."
    )

    def get_children(self) -> List['Criterion']:
        return list(self.criterions)
