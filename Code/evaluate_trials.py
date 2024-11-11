# evaluate_trials.py

import os
import json
import logging
from typing import List, Union

import rich
from models.trial import Trial
from models.criterion import (
    Category,
    Criterion,
    AtomicCriterion,
    CompoundCriterion,
    HierarchicalCriterion,
    NonsenseCriterion,
)
from services.criterion_evaluator import evaluate_atomic_criterion_with_llm

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def choose_directory() -> str:
    """
    Allows the user to navigate and choose a directory.
    """
    current_dir = os.getcwd()
    print(f"Current directory: {current_dir}")
    while True:
        print("\nContents:")
        items = os.listdir(current_dir)
        directories = [item for item in items if os.path.isdir(os.path.join(current_dir, item))]
        for idx, item in enumerate(directories):
            print(f"{idx}: {item}")
        print("Enter the number of the directory to navigate into, or 'c' to choose this directory, or '..' to go up:")
        choice = input("> ").strip()
        if choice == 'c':
            return current_dir
        elif choice == '..':
            current_dir = os.path.dirname(current_dir)
        elif choice.isdigit() and int(choice) < len(directories):
            selected_item = directories[int(choice)]
            selected_path = os.path.join(current_dir, selected_item)
            if os.path.isdir(selected_path):
                current_dir = selected_path
            else:
                print(f"'{selected_item}' is not a directory.")
        else:
            print("Invalid choice. Please try again.")

def load_trials_from_directory(directory: str) -> List[Trial]:
    """
    Loads JSON files from the specified directory into Trial models.
    """
    trials = []
    for filename in os.listdir(directory):
        if filename.endswith('.json'):
            filepath = os.path.join(directory, filename)
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    trial = Trial.model_validate(data)
                    trials.append(trial)
                    logger.info(f"Loaded trial from '{filename}'.")
            except Exception as e:
                logger.error(f"Failed to load '{filename}': {e}")
    return trials

def extract_atomic_criteria(trials: List[Trial]) -> List[AtomicCriterion]:
    """
    Extracts AtomicCriterion instances from the given trials.
    """
    atomic_criteria = []
    for trial in trials:
        if trial.structurized:
            atomic_criteria.extend(get_atomic_criteria(trial.structurized))
    return atomic_criteria

def get_atomic_criteria(
    criterion: Union[AtomicCriterion, CompoundCriterion, HierarchicalCriterion, NonsenseCriterion]
) -> List[AtomicCriterion]:
    """
    Recursively extracts AtomicCriterion instances from a criterion.
    """
    logger.debug(f"Extracting atomic criteria from: {criterion}")
    atomic_criteria = []
    if isinstance(criterion, NonsenseCriterion):
        return []
    rich.print(criterion)
    try:
        if criterion.category == Category.ATOMIC_CRITERION and isinstance(criterion, AtomicCriterion):
            atomic_criteria.append(criterion)
        elif criterion.category == Category.COMPOUND_CRITERION and isinstance(criterion, CompoundCriterion):
            for sub_criterion in criterion.criterions:
                atomic_criteria.extend(get_atomic_criteria(sub_criterion))
        elif criterion.category == Category.HIERARCHICAL_CRITERION and isinstance(criterion, HierarchicalCriterion):
            if criterion.parent_criterion:
                atomic_criteria.extend(get_atomic_criteria(criterion.parent_criterion))
            if criterion.child_criterion:
                atomic_criteria.extend(get_atomic_criteria(criterion.child_criterion))
        elif isinstance(criterion, NonsenseCriterion):
            # NonsenseCriterion does not contain any valid criteria
            pass
        else:
            logger.warning(f"Unknown criterion type: {type(criterion)}")
        return atomic_criteria
    except Exception as e:
        logger.error(f"Error extracting atomic criteria: {e}")
        return []
    

def main():
    print("Please choose a directory containing structured JSON files:")
    directory = choose_directory()
    print(f"Loading trials from directory: {directory}")
    trials = load_trials_from_directory(directory)
    if not trials:
        print("No trials loaded. Exiting.")
        return
    print(f"Loaded {len(trials)} trials.")
    for trial in trials:
        rich.print(trial)
    # Extract atomic criteria
    atomic_criteria = extract_atomic_criteria(trials)
    print(f"Extracted {len(atomic_criteria)} atomic criteria.")
    # Evaluate each atomic criterion
    for idx, atomic_criterion in enumerate(atomic_criteria, start=1):
        print(f"\nEvaluating criterion {idx}/{len(atomic_criteria)}:")
        if result := evaluate_atomic_criterion_with_llm(atomic_criterion):
            if result.satisfied is not None:
                if result.satisfied:
                    print("You meet this criterion.")
                else:
                    print("You do not meet this criterion.")
            if result.reasoning:
                print(f"Reasoning: {result.reasoning}")
            if result.message_to_user:
                print(f"Message: {result.message_to_user}")
        else:
            print("Evaluation could not be completed.")

if __name__ == "__main__":
    main()