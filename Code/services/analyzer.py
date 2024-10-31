# services/analyzer.py

import logging
from models.trial import Trial
from models.criterion import CategorizedCriterion
from utils.helpers import get_valid_input
import rich


logger = logging.getLogger(__name__)


def check_accuracy(trial: Trial):
    """
    Checks the accuracy of the structurized trial criteria by user input.

    Args:
        trial (Trial): The trial to analyze.
    """
    logger.info("Starting accuracy check for trial NCT ID: %s", trial.raw_data.nct_id)
    if not trial.structurized:
        logger.warning("Trial has no structurized data.")
        return

    def approve_criterion(criterion: CategorizedCriterion):
        print("\nReviewing Criterion:")
        rich.print(criterion)
        approval = get_valid_input(
            "Do you approve this criterion?", ["yes", "no"], print_options=True
        )
        if approval.lower() == "yes":
            logger.info("Criterion approved by user.")
        else:
            logger.info("Criterion disapproved by user.")

    def recurse_criteria(criterion: CategorizedCriterion):
        approve_criterion(criterion)
        for child in criterion.get_children():
            if isinstance(child, CategorizedCriterion):
                recurse_criteria(child)

    recurse_criteria(trial.structurized)
    logger.info("Accuracy check completed for trial NCT ID: %s", trial.raw_data.nct_id)
