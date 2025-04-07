# patient_matching/testing.py
import logging
import os
from typing import Set

from patient_matching.aggregated_trial_truth import (
    AggregatedTruthTable,
    TruthValue,
    aggregate_identified_trials,
)
from patient_matching.trial_overall_evaluator import (
    evaluate_trial_overall,
)
from patient_matching.truth_evaluator import update_truth_table_with_user_response
from patient_matching.user_answer_parser import (
    ConversationHistory,
    parse_user_response,
)

from src.models.identified_criteria import IdentifiedTrial
from src.models.logical_criteria import LogicalTrial
from src.repositories.trial_repository import (
    export_pydantic_to_json,
    load_pydantic_from_json,
    load_pydantic_models_from_folder,
)
from src.utils.config import DEFAULT_OUTPUT_DIR, setup_logging
from src.utils.helpers import get_non_empty_input

setup_logging(log_to_file=True, log_level=logging.INFO)


def get_trial_limit() -> int:
    """
    Prompt the user for how many trials to load.
    """
    while True:
        try:
            limit_str = input(
                "\nHow many trials would you like to load? (just press enter for all): "
            ).strip()
            if limit_str == "":
                return 0
            if limit_str.lower() in ["quit", "exit"]:
                logging.info("Exiting program.")
                exit()
            limit = int(limit_str)
            if limit >= 0:
                return limit
            print("Please enter a non-negative number.")
        except ValueError:
            print("Please enter a valid number.")


def main() -> None:
    logging.basicConfig(level=logging.INFO)

    # 1. Get number of trials to load
    limit = get_trial_limit()
    if limit == 0:
        logging.info("Loading all trials...")
    else:
        logging.info("Loading first %d trials...", limit)

    # 2. Load identified and logical trials
    identified_folder = os.path.join(DEFAULT_OUTPUT_DIR, "allTrials", "identified")
    logical_folder = os.path.join(DEFAULT_OUTPUT_DIR, "allTrials", "logical")

    identified_trials = load_pydantic_models_from_folder(
        identified_folder,
        IdentifiedTrial,
        file_extension="_identified.json",
        limit=limit if limit > 0 else None,
    )
    logging.info("Loaded %d identified trials", len(identified_trials))
    remaining_trialIDs = {trial.info.nct_id for trial in identified_trials}
    removed_trials: Set[str] = set()

    # 3. Create initial aggregated truth table using identified trials
    aggregator: AggregatedTruthTable = aggregate_identified_trials(identified_trials)

    matching_folder = os.path.join(DEFAULT_OUTPUT_DIR, "matching")
    os.makedirs(matching_folder, exist_ok=True)

    # 4. Save initial aggregator
    export_pydantic_to_json(aggregator, "aggregated_truth.json", matching_folder)
    logging.info(
        "Initial aggregator saved to %s",
        os.path.join(matching_folder, "aggregated_truth.json"),
    )

    # 5. Initialize conversation history
    conversation_history = ConversationHistory()

    # 6. Enter user input loop
    logging.info("Entering user response loop. Type 'quit' or 'exit' to stop.")

    while True:
        # Get user input
        question = get_non_empty_input("\nEnter your question (or 'quit' to exit): ")
        user_input = get_non_empty_input("\nEnter your response:")

        try:
            # Parse user response
            parsed_response = parse_user_response(user_input, question)
            conversation_history.add_response(question, parsed_response.parsed_answers)
            export_pydantic_to_json(
                conversation_history,
                "conversation_history.json",
                matching_folder,
            )

            # Update truth table and track modified trials
            if modified_trials := {
                trial_id
                for criterion in parsed_response.parsed_answers
                for trial_id in update_truth_table_with_user_response(
                    criterion, aggregator
                )
            }:
                logging.info("Updated truth values for %d trials", len(modified_trials))
                logging.info("Modified trials: %s", modified_trials)
            else:
                logging.info("No trials were affected by this response")

            # Evaluate remaining trials
            newly_removed = set()
            for trial_id in modified_trials:
                trial = load_pydantic_from_json(
                    logical_folder, f"{trial_id}_logical.json", LogicalTrial
                )
                if trial is None:
                    logging.warning("Trial %s not found", trial_id)
                    continue
                result = evaluate_trial_overall(trial, aggregator)
                if result.overall_truth == TruthValue.FALSE:
                    removed_trials.add(trial.info.nct_id)
                    newly_removed.add(trial.info.nct_id)
                    logging.info(
                        "Trial %s removed due to %s eligibility status",
                        trial.info.nct_id,
                        result.overall_truth,
                    )

            # Update remaining trials
            remaining_trialIDs = remaining_trialIDs - newly_removed

            # Print results
            print(f"\nRemaining trials: {len(remaining_trialIDs)}")
            if remaining_trialIDs:
                for trial_id in remaining_trialIDs:
                    print(f"- {trial_id}")
            print(f"Total removed trials: {len(removed_trials)}")
            print(f"Newly removed trials: {len(newly_removed)}")
            if newly_removed:
                for trial_id in newly_removed:
                    print(f"- {trial_id}")

            # Save updated aggregator
            export_pydantic_to_json(
                aggregator,
                "aggregated_truth.json",
                matching_folder,
            )

        except Exception as e:
            logging.error("Error processing user input: %s", e)
            continue

    logging.info("Exiting user response loop.")


if __name__ == "__main__":
    main()
