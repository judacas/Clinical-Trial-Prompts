import csv
import logging
import os

from src.repositories.trial_repository import export_pydantic_to_json
from src.services.trial_manager import parse_study_to_raw_trial
from src.utils.config import DEFAULT_OUTPUT_DIR
from src.utils.helpers import curl_with_status_check

CSV_PATH = os.path.join(os.path.dirname(__file__), "us_trials_nct_numbers.csv")
RAW_OUTPUT_DIR = os.path.join(DEFAULT_OUTPUT_DIR, "recent_us", "raw")
os.makedirs(RAW_OUTPUT_DIR, exist_ok=True)

BATCH_SIZE = 100  # don't exceed 1000, or we gotta start doing pagination, actually don't exceed who knows what the limit is due to too large uri but 100 works fine
FAILED_FILE = os.path.join(RAW_OUTPUT_DIR, "failed_trials.txt")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def importTrials():
    with open(CSV_PATH, newline="") as csv_file:
        reader = csv.reader(csv_file)
        nct_ids = [row[0].strip() for row in reader if row and row[0].strip()]

    logger.info(f"Loaded {len(nct_ids)} NCT IDs from CSV.")
    failed_nct_ids = []

    for i in range(0, len(nct_ids), BATCH_SIZE):
        batch = nct_ids[i : i + BATCH_SIZE]
        logger.info(f"Fetching batch {i//BATCH_SIZE+1}: {len(batch)} trials")
        try:
            ids_param = "%2c".join(batch)
            url = f"https://clinicaltrials.gov/api/v2/studies?format=json&query.cond={ids_param}&fields=NCTId%7CEligibilityModule%7COfficialTitle&pageSize={BATCH_SIZE}"
            # ids_param = ",".join(batch)
            # url = f"https://clinicaltrials.gov/api/v2/studies?ids={ids_param}&fields=NCTId,EligibilityModule,OfficialTitle"
            data = curl_with_status_check(url)
            studies = data.get("studies", [])
            # Check for missing NCT IDs in the response
            returned_ids = {
                study.get("protocolSection", {})
                .get("identificationModule", {})
                .get("nctId", None)
                or study.get("NCTId", None)
                for study in studies
            }
            if missing_ids := set(batch) - returned_ids:
                logger.warning(f"Missing NCT IDs in response: {missing_ids}")
                failed_nct_ids.extend(missing_ids)
            for j, study in enumerate(studies):
                nct_id = batch[j] if j < len(batch) else "UNKNOWN"
                try:
                    raw_trial = parse_study_to_raw_trial(
                        study.get("protocolSection", study)
                    )
                    file_name = f"{nct_id}_raw.json"
                    success = export_pydantic_to_json(
                        raw_trial, file_name, RAW_OUTPUT_DIR
                    )
                    if not success:
                        failed_nct_ids.append(nct_id)
                except Exception as e:
                    logger.error(f"Failed to process/save trial {nct_id}: {e}")
                    failed_nct_ids.append(nct_id)
        except Exception as e:
            logger.error(f"Failed to fetch/save batch {i//BATCH_SIZE+1}: {e}")
            failed_nct_ids.extend(batch)
    # Save failed NCT IDs to file
    if failed_nct_ids:
        with open(FAILED_FILE, "w", encoding="utf-8") as f:
            for nct_id in failed_nct_ids:
                f.write(nct_id + "\n")
        logger.error(f"Failed NCT IDs saved to {FAILED_FILE}")
    else:
        logger.info("All trials processed and saved successfully.")


if __name__ == "__main__":
    importTrials()
