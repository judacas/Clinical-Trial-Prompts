# services/structurizer.py

import logging
from typing import Optional, Union
from models.criterion import (
    Criterion,
    CategorizedCriterion,
    AtomicCriterion,
    HierarchicalCriterion,
    CompoundCriterion,
    Category,
)
from utils.openai_client import get_openai_client
from pydantic import BaseModel
import rich

# Configure logging
logger = logging.getLogger(__name__)

client = get_openai_client()


class IndividualAnalysis(BaseModel):
    """
    Represents the analysis of a criterion for a specific category.
    """
    category: Category
    thoughts: str
    decision: bool


class CategorizingStructure(BaseModel):
    """
    Represents the structure for categorizing a criterion.
    """
    individual_analyses: list[IndividualAnalysis]
    overall_thoughts: str
    final_category: Category


def categorize_criterion(criterion: Criterion, verbose: bool = False) -> Optional[CategorizedCriterion]:
    """
    Categorizes a given criterion using the OpenAI model.

    Args:
        criterion (Criterion): The criterion to categorize.
        verbose (bool): Whether to print detailed output.

    Returns:
        Optional[CategorizedCriterion]: The categorized criterion or None if failed.
    """
    logger.info("Categorizing criterion: %s", criterion.raw_text)
    try:
        completion = client.beta.chat.completions.parse(
            model="gpt-4o-2024-08-06",
            messages=[
                {
                    "role": "system",
                    "content": "You are an expert in categorizing clinical trial eligibility criteria.",
                },
                {"role": "user", "content": criterion.raw_text},
            ],
            temperature=0.0,
            response_format=CategorizingStructure,
        )
        message = completion.choices[0].message
        if message.parsed:
            if verbose:
                rich.print(message.parsed)
            for analysis in message.parsed.individual_analyses:
                if analysis.category == message.parsed.final_category:
                    categorized = CategorizedCriterion(
                        raw_text=criterion.raw_text,
                        category=message.parsed.final_category,
                        category_reasoning=analysis.thoughts,
                        overall_thoughts=message.parsed.overall_thoughts,
                    )
                    logger.info("Categorized criterion as %s", categorized.category)
                    return categorized
        else:
            if verbose:
                rich.print(message.refusal)
            logger.warning("Failed to parse categorization response.")
            return None
    except Exception as e:
        logger.error("Error during categorization: %s", e)
        return None


def structurize_once(
    criterion: CategorizedCriterion, verbose: bool = False
) -> Optional[Union[AtomicCriterion, HierarchicalCriterion, CompoundCriterion]]:
    """
    Structurizes a categorized criterion based on its category.

    Args:
        criterion (CategorizedCriterion): The categorized criterion to structurize.
        verbose (bool): Whether to print detailed output.

    Returns:
        Optional[Union[AtomicCriterion, HierarchicalCriterion, CompoundCriterion]]: The structurized criterion or None if failed.
    """
    logger.info("Structurizing criterion: %s", criterion.raw_text)
    category_to_response_format = {
        Category.ATOMIC_CRITERION: AtomicCriterion,
        Category.HIERARCHICAL_CRITERION: HierarchicalCriterion,
        Category.COMPOUND_CRITERION: CompoundCriterion,
    }

    prompt = (
        "You are part of an NLP pipeline designed to structurize clinical trial eligibility criteria."
        " Parse the criterion below into its components."
    )

    try:
        completion = client.beta.chat.completions.parse(
            model="gpt-4o-2024-08-06",
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": criterion.raw_text},
            ],
            response_format=category_to_response_format[criterion.category],
            temperature=0.0,
        )
        if response := completion.choices[0].message.parsed:
            if verbose:
                rich.print(response)
            logger.info("Successfully structurized criterion.")
            return response
        else:
            logger.warning("Failed to parse structurization response.")
            return None
    except Exception as e:
        logger.error("Error during structurization: %s", e)
        return None


def structurize_fully(
    criterion: Criterion, verbose: bool = False
) -> Optional[Union[AtomicCriterion, HierarchicalCriterion, CompoundCriterion]]:
    """
    Recursively structurizes a criterion fully into its components.

    Args:
        criterion (Criterion): The criterion to structurize.
        verbose (bool): Whether to print detailed output.

    Returns:
        Optional[Union[AtomicCriterion, HierarchicalCriterion, CompoundCriterion]]: The fully structurized criterion or None if failed.
    """
    logger.info("Starting full structurization for criterion.")
    categorized = categorize_criterion(criterion, verbose)
    if not categorized:
        logger.warning("Categorization failed.")
        return None

    structured = structurize_once(categorized, verbose)
    if not structured:
        logger.warning("Structurization failed.")
        return None

    if isinstance(structured, AtomicCriterion):
        return structured
    elif isinstance(structured, HierarchicalCriterion):
        structured.parent_criterion = structurize_fully(
            structured.parent_criterion, verbose
        )
        structured.child_criterion = structurize_fully(
            structured.child_criterion, verbose
        )
        return structured
    elif isinstance(structured, CompoundCriterion):
        structured.criterions = [
            structurize_fully(crit, verbose) for crit in structured.criterions
        ]
        return structured
    else:
        logger.error("Unknown criterion type.")
        return None
