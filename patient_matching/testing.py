# patient_matching/testing.py
import logging
import os
from datetime import datetime
from typing import List

from patient_matching.aggregated_trial_truth import (
    AggregatedTruthTable,
    aggregate_identified_trials,
)
from patient_matching.truth_evaluator import update_truth_table_with_user_response
from patient_matching.user_answer_parser import (
    ConversationHistory,
    UserAnswerHistory,
    parse_user_response,
)

from src.models.identified_criteria import IdentifiedTrial

# Imports from your existing codebase
from src.repositories.trial_repository import (
    export_pydantic_to_json,
    load_pydantic_from_json,
)
from src.utils.config import DEFAULT_OUTPUT_DIR


def main() -> None:
    logging.basicConfig(level=logging.INFO)

    # 1. Read all identified trial JSON files from the "identified" folder.
    identified_folder = os.path.join(DEFAULT_OUTPUT_DIR, "allTrials", "identified")
    trial_files = [f for f in os.listdir(identified_folder) if f.endswith(".json")]

    identified_trials: List[IdentifiedTrial] = []
    for file_name in trial_files:
        if trial := load_pydantic_from_json(
            identified_folder, file_name, IdentifiedTrial
        ):
            identified_trials.append(trial)
        else:
            logging.warning("Failed to load trial file: %s", file_name)

    # 2. Aggregate them into a single truth table
    aggregator: AggregatedTruthTable = aggregate_identified_trials(identified_trials)

    matching_folder = os.path.join(
        DEFAULT_OUTPUT_DIR,
        "matching",
    )
    # 3. Save the resulting aggregator before any user input (just for inspection)
    export_pydantic_to_json(aggregator, "aggregated_truth.json", matching_folder)
    logging.info(
        "Initial aggregator saved to %s",
        os.path.join(matching_folder, "aggregated_truth.json"),
    )

    # 4. Enter a user input loop to simulate real-time updates.
    logging.info("Entering user response loop. Type 'quit' or 'exit' to stop.")

    # Initialize conversation history
    conversation_history = ConversationHistory()

    while True:
        question = input(
            "\nEnter the question to ask the user (or 'quit' to exit): "
        ).strip()
        if question.lower() in ["quit", "exit"]:
            logging.info("Exiting loop.")
            break

        user_input = input("\nEnter a user response (or 'quit' to exit): ").strip()
        if user_input.lower() in ["quit", "exit"]:
            logging.info("Exiting loop.")
            break

        # Parse the user response into structured user data
        try:
            user_data: UserAnswerHistory = parse_user_response(user_input, question)

            # Add the response to the conversation history
            conversation_history.add_response(question, user_data.parsed_answers)

            # Save the updated conversation history
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            history_filename = f"conversation_history_{timestamp}.json"
            export_pydantic_to_json(
                conversation_history, history_filename, matching_folder
            )
            logging.info(f"Conversation history saved to {history_filename}")

        except Exception as e:
            logging.error("Error parsing user response: %s", e)
            continue

        # For each parsed criterion in the user data, update the aggregator
        for parsed_criterion in user_data.parsed_answers:
            aggregator = update_truth_table_with_user_response(
                parsed_criterion, aggregator
            )

        # Optionally, save the updated aggregator to inspect changes.
        export_pydantic_to_json(
            aggregator, "aggregated_truth_updated.json", matching_folder
        )
        logging.info("Aggregator updated and re-saved.")


if __name__ == "__main__":
    main()
