# utils/config.py
"""
Configuration Module for Clinical Trial Analysis

This module manages configuration settings and logging setup for the clinical trial analysis
application. It defines project paths, logging formats, and provides utility functions for
configuring logging behavior.

The module handles:
1. Project directory and file path definitions
2. Colored console logging configuration
3. File logging setup with timestamped log files
4. Log level and format configurations

Classes:
    ColoredFormatter: Custom formatter that adds color to console logs based on severity.

Functions:
    setup_logging: Configure application-wide logging.
    setup_file_logging: Set up logging to a file with appropriate formatting.
"""

import logging
import os
from datetime import datetime

# Get the project root directory (one level up from Code)
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

# Define output directory relative to project root
# This ensures consistent output paths regardless of execution directory
DEFAULT_OUTPUT_DIR = os.path.join(PROJECT_ROOT, "output")

TIMEOUT = 30
TEMPERATURE = 0.0

# Maximum number of concurrent OpenAI calls
MAX_CONCURRENT_OPENAI_CALLS = 100


class ColoredFormatter(logging.Formatter):
    """
    Custom formatter that adds color to console logs based on severity.
    """

    # ANSI escape codes for colors
    COLORS = {
        "DEBUG": "\033[92m",  # Green
        "INFO": "\033[94m",  # Blue
        "WARNING": "\033[93m",  # Yellow
        "ERROR": "\033[91m",  # Red
        "CRITICAL": "\033[91m",  # Red
    }
    RESET = "\033[0m"  # Reset color code

    def format(self, record):
        """
        Format the log record with appropriate colors.

        Args:
            record: The log record to format.

        Returns:
            str: The formatted, color-coded log message.
        """
        log_color = self.COLORS.get(record.levelname, self.RESET)
        formatted_message = super().format(record)
        return f"{log_color}{formatted_message}{self.RESET}"


def setup_logging(log_level=logging.INFO, log_to_file=False, log_dir="logs"):
    """
    Set up application-wide logging configuration.

    Args:
        log_level (int): The logging level (e.g., logging.DEBUG, logging.INFO)
        log_to_file (bool): Whether to save logs to a file
        log_dir (str): Directory to store log files if log_to_file is True

    Returns:
        logging.Logger: The configured root logger.
    """
    # Create formatters
    console_formatter = ColoredFormatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    file_formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Create console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(console_formatter)

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)

    # Remove existing handlers to prevent duplicate logs
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # Add console handler
    root_logger.addHandler(console_handler)

    # Add file handler if requested
    if log_to_file:
        setup_file_logging(log_dir, logging, file_formatter, root_logger)

    return root_logger


def setup_file_logging(log_dir, logging, file_formatter, root_logger):
    """
    Set up logging to a file with timestamped filename.

    Args:
        log_dir (str): Directory to store log files
        logging: The logging module
        file_formatter: The formatter to use for file logs
        root_logger: The root logger to attach the file handler to
    """
    # Create logs directory if it doesn't exist
    os.makedirs(log_dir, exist_ok=True)

    # Create log file with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = os.path.join(log_dir, f"clinical_trial_analysis_{timestamp}.log")

    # Set up file handler with the configured formatter
    file_handler = logging.FileHandler(log_file)
    file_handler.setFormatter(file_formatter)
    root_logger.addHandler(file_handler)

    root_logger.info(f"Logging to file: {log_file}")
