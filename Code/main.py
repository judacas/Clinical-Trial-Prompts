# main.py

import logging
from services.trial_manager import process_trial
from repositories.trial_repository import save_trial
from services.analyzer import check_accuracy

class ColoredFormatter(logging.Formatter):
    # ANSI escape codes for colors
    COLORS = {
        'DEBUG': '\033[92m',    # Green
        'INFO': '\033[94m',     # Blue
        'WARNING': '\033[93m',  # Yellow
        'ERROR': '\033[91m',    # Red
        'CRITICAL': '\033[91m', # Red
    }
    RESET = '\033[0m'

    def format(self, record):
        log_color = self.COLORS.get(record.levelname, self.RESET)
        formatted_message = super().format(record)
        return f"{log_color}{formatted_message}{self.RESET}"

def main():
    # Configure logging here
    formatter = ColoredFormatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt=None,
        style='%'
    )

    handler = logging.StreamHandler()
    handler.setFormatter(formatter)

    logging.basicConfig(
        level=logging.INFO,  # Set to DEBUG to capture debug messages
        handlers=[handler]
    )

    logger = logging.getLogger(__name__)

    trials_to_process = []

    while nct_id := input("Enter the NCT ID of the trial you want to process (or press Enter to finish): ").strip():
        trials_to_process.append(nct_id)

    for nct_id in trials_to_process:
        logger.info("Processing trial NCT ID: %s", nct_id)
        if trial := process_trial(nct_id, verbose=True):
<<<<<<< HEAD
            file_name = f"{nct_id}_structured.json"
=======
            file_name = f"{nct_id}_newly_structured.json"
>>>>>>> 0fc8b9f9 (attempting to fix lost git history)
            output_folder = "output"

            if save_trial(trial, output_folder, file_name):
                logger.info("Trial saved successfully.")
                # Check approval
                # check_accuracy(trial)
            else:
                logger.error("Failed to save trial.")
        else:
            logger.error("Failed to process trial NCT ID: %s", nct_id)

if __name__ == "__main__":
    main()
