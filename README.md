# ClearMatch

A Python tool for the structured analysis of clinical trial eligibility criteria by extracting and organizing atomic criteria into logical structures.

## Overview

ClearMatch processes clinical trial data from **ClinicalTrials.gov**, extracting structured information about eligibility criteria. It performs three key steps:

1. **Identification** – Extracts atomic criteria from raw text.
2. **Logical Structuring** – Organizes these criteria into logical relationships.
3. **Matching Patients to Oncological Clinical Trials** – *(Not implemented yet).*

## Features

- Fetches clinical trial data from the **ClinicalTrials.gov API**.
- Breaks down complex eligibility criteria into **atomic components**.
- Structures criteria using **logical operators** (`AND`, `OR`, `NOT`, `XOR`, `CONDITIONAL`).
- Persists processed data as **JSON files** for further analysis.

## Requirements

- **Python 3.8+**
- **OpenAI API key** (for GPT-4o access)

## Installation

1. **Navigate to the directory where you want to clone the repository:**
    ```sh
    cd ~/path/to/repo/
    ```

2. **Clone this repository:**
    ```sh
    gh repo clone judacas/Clinical-Trial-Prompts
    ```
    *This uses [GitHub CLI](https://cli.github.com/). If you don’t have it, use:*
    ```sh
    git clone https://github.com/judacas/Clinical-Trial-Prompts.git
    ```

3. **Enter the project directory:**
    ```sh
    cd Clinical-Trial-Prompts
    ```

4. *(Optional but Recommended)* **Create and activate a virtual environment:**
    ```sh
    python -m venv .venv
    source .venv/bin/activate  # On macOS/Linux
    .venv\Scripts\activate     # On Windows (Command Prompt)
    ```

5. **Install dependencies:**
    ```sh
    pip install -r requirements.txt
    ```

6. **Set up environment variables:**

    **For CLI users (Linux/macOS/Windows Command Line):**
    Run the following commands to create a new `.env` file inside `src/` and remove `sample.env`:
    
    ```sh
    echo 'OPENAI_API_KEY="your-api-key-here"' > src/.env
    rm src/sample.env  # Remove the sample file
    ```

    *(Replace `"your-api-key-here"` with your actual OpenAI API key.)*

    To verify the contents of `.env`, you can run:
    ```sh
    cat src/.env
    ```

    **For GUI users (Windows Explorer/macOS Finder):**
    - Navigate to the **`src/`** directory inside the project.
    - **Rename** `sample.env` to `.env`.
    - Open `.env` with a text editor (Notepad, VS Code, etc.).
    - Replace `your-api-key-here` with your actual API key.
    - Save and close the file.

    **Make sure `src/.env` is not committed to Git** (it’s already in `.gitignore`).


---

## **Usage**

To run ClearMatch, simply execute the main script:

```sh
python -m scripts.main
```

Follow the command-line instructions to process and structure clinical trial data.

---

## **Project Structure**
```
Clinical-Trial-Prompts/
│── models/          # Pydantic data models
│── services/        # Business logic components
│── repositories/    # Data persistence layer
│── utils/           # Helper functions and utilities
│── scripts/         # Entry points for execution
```

---

## **Data Flow**

1. **Raw trial data** is fetched from **ClinicalTrials.gov**.
2. The text is **processed** to extract atomic eligibility criteria.
3. Criteria are **organized into logical structures**.
4. The results are **stored as structured JSON files** for further use.
---