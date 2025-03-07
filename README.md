# ClearMatch

A Python tool for structured analysis of clinical trial eligibility criteria by extracting and organizing atomic criteria into logical structures.

## Overview

This project processes clinical trial data from ClinicalTrials.gov, extracting structured information about eligibility criteria. It performs two key steps:

1. **Identification**: Extracts atomic criteria from raw text
2. **Logical Structurization**: Organizes these criteria into logical relationships

3. **Matching of patients to Oncological Clinical Trials**: Not implemented yet

## Features

- Fetches clinical trial data from ClinicalTrials.gov API
- Breaks down complex eligibility criteria into atomic components
- Structures criteria using logical operators (AND, OR, NOT, XOR, Conditional)
- Persists processed data as JSON files

## Requirements

- Python 3.8+
- OpenAI API key (for GPT-4o access)

## Installation

1. Clone this repository
    ```
    gh repo clone judacas/Clinical-Trial-Prompts
    ```
    note: above uses [github cli](https://cli.github.com/)

2. cd into wherever you cloned the repo to
    ```
    cd path/to/repo/root
    ```

2. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

3. Set up environment variables:
    Edit `sample.env` to add your OpenAI API key.
    rename `sample.env` to `.env`

## Usage
simply run the main file

```python
python -m scripts.main
```

now follow the command line instructions to structurize whichever clinical trials you wish

## Project Structure

- `models/`: Pydantic data models
- `services/`: Business logic components
- `repositories/`: Data persistence layer
- `utils/`: Helper functions and utilities

## Data Flow

1. Raw trial data is fetched from ClinicalTrials.gov
2. Text is processed to extract atomic criteria
3. Criteria are organized into logical structures
4. Results are stored as JSON files
