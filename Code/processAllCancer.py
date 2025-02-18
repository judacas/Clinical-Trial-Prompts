# main.py
import logging
import os
from services.trial_manager import process_trial


class ColoredFormatter(logging.Formatter):
    # ANSI escape codes for colors
    COLORS = {
        "DEBUG": "\033[92m",  # Green
        "INFO": "\033[94m",  # Blue
        "WARNING": "\033[93m",  # Yellow
        "ERROR": "\033[91m",  # Red
        "CRITICAL": "\033[91m",  # Red
    }
    RESET = "\033[0m"

    def format(self, record):
        log_color = self.COLORS.get(record.levelname, self.RESET)
        formatted_message = super().format(record)
        return f"{log_color}{formatted_message}{self.RESET}"


def main():
    # Configure logging here
    formatter = ColoredFormatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s", datefmt=None, style="%"
    )

    handler = logging.StreamHandler()
    handler.setFormatter(formatter)

    logging.basicConfig(
        level=logging.INFO, handlers=[handler]  # Set to DEBUG to capture debug messages
    )

    logger = logging.getLogger(__name__)

    onlyCancerFolder = os.path.join("..","Trials", "CHIA", "OnlyCancerTrials")
    trials_to_process = [
        file.split(".")[0]
        for file in os.listdir(onlyCancerFolder)
        if file.endswith(".json")
    ]
    trials_to_process = trials_to_process[10:] # note this is only because I had already processed the first 10 trials
    print(trials_to_process)
    print(len(trials_to_process))
    errors = 0
    for nct_id in trials_to_process:
        logger.info("Processing trial NCT ID: %s", nct_id)
        try:
            process_trial(nct_id)
        except Exception as e:
            errors += 1
            logger.error("Error processing trial: %s", e)
    logger.info("Finished processing trials. %s fatal errors occurred.", errors)


if __name__ == "__main__":
    main()
