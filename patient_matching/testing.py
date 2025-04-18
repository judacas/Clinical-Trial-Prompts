# patient_matching/testing.py
import json
import logging
import os
from typing import Dict

from patient_matching.aggregated_trial_truth import (
    AggregatedTruthTable,
    TruthValue,
    aggregate_identified_trials,
)
from patient_matching.trial_overall_evaluator import evaluate_all_trials
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

setup_logging(log_to_file=True, log_level=logging.DEBUG)


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


def has_unknowns(status_map: Dict[str, TruthValue]) -> bool:
    """
    Check if there are any trials with an UNKNOWN truth value in the status map.

    Args:
        status_map (Dict[str, TruthValue]): A dictionary mapping trial IDs to their truth values.

    Returns:
        bool: True if there are UNKNOWN truth values, False otherwise.
    """
    return any(value == TruthValue.UNKNOWN for value in status_map.values())


def main() -> None:  # sourcery skip: dict-assign-update-to-union
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
    # Load all logical trials into memory
    logical_trials: Dict[str, LogicalTrial] = {}
    for trial in identified_trials:
        trial_id = trial.info.nct_id
        model = load_pydantic_from_json(
            logical_folder, f"{trial_id}_logical.json", LogicalTrial
        )
        if model is None:
            logging.warning("Logical model for trial %s not found", trial_id)
        else:
            logical_trials[trial_id] = model
    # 3. Create initial aggregated truth table using identified trials
    aggregator: AggregatedTruthTable = aggregate_identified_trials(identified_trials)
    # Initial status map: evaluate all trials once
    status_list = evaluate_all_trials(list(logical_trials.values()), aggregator)
    status_map: Dict[str, TruthValue] = {
        res.trial_id: res.overall_truth for res in status_list
    }

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

    while has_unknowns(status_map):
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

            # NOTE: we don't need to re-evaluate trials that are already False since they won't change
            # however once we change to an analog value for truth evaluation, we may need to re-evaluate all trials
            if to_eval_ids := [
                tid
                for tid in modified_trials
                if status_map.get(tid, TruthValue.UNKNOWN) != TruthValue.FALSE
            ]:
                to_eval_models = [logical_trials[tid] for tid in to_eval_ids]
                new_results = evaluate_all_trials(to_eval_models, aggregator)
            else:
                new_results = []
            status_map.update({res.trial_id: res.overall_truth for res in new_results})

            # Print affected trials summary, sorted by truth value then NCTID
            print(f"\n{len(new_results)} trials affected.\n")
            # Sort by truth value (as string for stable ordering), then by NCTID
            sorted_results = sorted(
                new_results, key=lambda res: (str(res.overall_truth), res.trial_id)
            )
            for res in sorted_results:
                print(f"{res.trial_id}: {res.overall_truth}")

            # Save updated aggregator
            export_pydantic_to_json(
                aggregator, "aggregated_truth.json", matching_folder
            )

            # Save trial truth map
            try:
                truth_map_path = os.path.join(matching_folder, "trial_truth_map.json")
                with open(truth_map_path, "w", encoding="utf-8") as f:
                    json.dump(
                        {tid: val.value for tid, val in status_map.items()}, f, indent=4
                    )
                logging.info("Trial truth map saved to %s", truth_map_path)
            except Exception as e:
                logging.error("Failed to save trial truth map: %s", e)

        except Exception as e:
            logging.error("Error processing user input: %s", e)
            continue

    logging.info("Exiting user response loop.")


if __name__ == "__main__":
    main()
