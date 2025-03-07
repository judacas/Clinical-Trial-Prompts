import os

# Get the project root directory (one level up from Code)
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))

# Define output directory relative to project root (assures that the output will not change if you call the script from a different directory)
DEFAULT_OUTPUT_DIR = os.path.join(PROJECT_ROOT, 'output')