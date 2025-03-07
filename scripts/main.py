# main.py
import logging
import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from src.services.trial_manager import process_trial

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
    
def getCancerTrials() -> list[str]:
    onlyCancerFolder = os.path.join("..","Trials", "CHIA", "OnlyCancerTrials")
    return [
        file.split(".")[0]
        for file in os.listdir(onlyCancerFolder)
        if file.endswith(".json")
    ]
    
def getTrialsFromUser() -> list[str]:
    trials = []
    while nct_id := input("Enter the NCT ID of the trial you want to process (or press Enter to finish): ").strip():
        trials.append(nct_id)
    return trials

def get_trials()-> list[str] | None:
    while True:
        user_choice = input("Please choose one of the following\n'm' for manual input\n'a' to process all cancer trials\n'q' to quit: ").strip().lower()

        if user_choice == 'm':
            return getTrialsFromUser()
        elif user_choice == 'a':
            return getCancerTrials()
        elif user_choice == 'q':
            return None
        else:
            print("Invalid choice. Please try again.")

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
    
    
    trials = get_trials()
    if not trials:
        print("Exiting...")
        return
    
    for nct_id in trials:
        logger.info("Processing trial NCT ID: %s", nct_id)
        process_trial(nct_id)

if __name__ == "__main__":
    main()
