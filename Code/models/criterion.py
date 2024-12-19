# models/criterion.py
from __future__ import annotations
from enum import Enum
from pydantic import BaseModel, Field
from typing import List, Optional, Sequence, Union


class Category(str, Enum):
    """
    Enum representing the category of a cancer clinical criterion. Note that for all of these it is the outermost category, should there be a Compound_Criterion composed of an atomic and a hierarchical criterion, then the resulting category would be Compound_Criterion as it is the outermost category.
    """
    ATOMIC_CRITERION = "atomic_Criterion- where there is only one criterion that can be answered with a simple question (if there are multiple atomic then it is either compound or hierarchical)"
    COMPOUND_CRITERION = "compound_Criterion- when there are two or more individual criterions which can be separated into various atomic or hierarchical criterions."
    HIERARCHICAL_CRITERION = "hierarchical_criterion- when there is a parent criterion and a child criterion which adds further criteria should the parent be true."
    NONSENSE_CRITERION = "nonsense- when the criterion is not a valid criterion"


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
    parent_criterion: Union[Criterion, AtomicCriterion, HierarchicalCriterion, CompoundCriterion] = Field(..., description="The parent criterion.")
    child_criterion: Criterion = Field(..., description="The child criterion modifying the parent.")
    additional_information: List[str] = Field(
        ..., description="Additional context for the criterion."
    )

    def get_children(self) -> List['Criterion']:
        return [self.parent_criterion, self.child_criterion]

class NonsenseCriterion(CategorizedCriterion):
    """
    Represents a nonsense criterion that is not valid.
    """
    raw_text: str = Field(..., description="The raw text of the criterion.")
    error_message: str = Field(..., description="Error message indicating why the criterion is invalid.")
    def get_children(self) -> List['Criterion']:
        return []


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
    criterions: Sequence[Union[Criterion, AtomicCriterion, HierarchicalCriterion, CompoundCriterion]] = Field(
        ..., description="List of criteria in the compound criterion."
    )

    def get_children(self) -> List['Criterion']:
        return list(self.criterions)
