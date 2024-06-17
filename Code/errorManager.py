# logging_config.py
import logging
import os
from datetime import datetime
import traceback

log_dir = os.path.join(os.getcwd(), 'errorLogs')
os.makedirs(log_dir, exist_ok=True)
log_file = os.path.join(log_dir, f'{datetime.now().strftime("%Y-%m-%d")}.txt')
logging.basicConfig(filename=log_file, level=logging.ERROR)

def logError(customText = None, e = None, during = None):
    if customText is not None:
        print(f"\033[91m An error occurred{((' during ' + during) if during is not None else '')}. Please check the logs. \033[0m")
        logging.error(customText + (f" during {during}" if during is not None else ""))
        if e is not None:
            logging.error(f"Here is the error:\n{e}\n{traceback.format_exc()}") 
    elif e is not None:
        print(f"\033[91m An error occurred{((' during ' + during) if during is not None else '')}. Please check the logs. \033[0m")
        logging.error("You messed up" + (f" during {during}" if during is not None else ". ") +  f"Here is the error:\n{e}\n{traceback.format_exc()}")
    else:
        print("\033[91m come on now, you can't be causing an error when trying to log an error, include either the error or some custom message please, go check the log now to see what actually happened \033[0m")
        logging.error("Verschlimmbesserung during error logging")