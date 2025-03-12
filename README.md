# ClearMatch

A Python tool for the structured analysis of clinical trial eligibility criteria by extracting and organizing atomic criteria into logical structures.

## 🚀 Overview

ClearMatch processes clinical trial data from **ClinicalTrials.gov**, extracting structured information about eligibility criteria. It performs three key steps:

1. **Identification** – Extracts atomic criteria from raw text.
2. **Logical Structuring** – Organizes these criteria using logical relationships (`AND`, `OR`, `NOT`, `XOR`, `CONDITIONAL`).
3. **Matching Patients to Oncological Clinical Trials** – _(Planned but not yet implemented)._

### **✅ Features**
- ✅ Fetches clinical trial data from the **ClinicalTrials.gov API**.
- ✅ Extracts and structures **eligibility criteria** into logical expressions.
- ✅ Persists processed data as **JSON files** for further analysis.
- 🚧 **Upcoming:** Automated patient matching system.
- 🚧 **Upcoming:** UI.

---

## **📋 Requirements**
- **Python 3.13+**
- **OpenAI API key** (for GPT-4o access)
  📌 **Get your API key here:** [OpenAI API Keys](https://platform.openai.com/api-keys)

---

## **💾 Installation**

1️⃣ **Clone the repository**
```sh
   gh repo clone judacas/Clinical-Trial-Prompts
   ```

   _This uses [GitHub CLI](https://cli.github.com/). If you don’t have it, use:_

   ```sh
   git clone https://github.com/judacas/Clinical-Trial-Prompts.git
   ```
make sure to then cd into the root directory
```sh
cd Clinical-Trial-Prompts
```

2️⃣ **Set up a virtual environment _(Optional but Recommended)_ **
```sh
python -m venv .venv
source .venv/bin/activate  # macOS/Linux
.venv\Scripts\activate     # Windows
```

3️⃣ **Install dependencies**
```sh
pip install -r requirements.txt
```

4️⃣ **Set up environment variables**
Copy the example [`sample.env`](src/sample.env) file and rename it to proper `.env` naming convention:
```sh
cp src/sample.env src/.env  # macOS/Linux
copy src\sample.env src\.env  # Windows
```

To edit the `.env` file in the terminal, use:
```sh
nano src/.env  # Linux/macOS
notepad src\.env  # Windows
```
Then, add your OpenAI API key:
```sh
OPENAI_API_KEY="your-api-key-here"
```

📌 **Note:** The `.env` file is ignored by Git to prevent accidental key exposure.

---

## **🛠 Usage**
Run ClearMatch using:
```sh
python -m src.main
```
Follow the command-line instructions to process and structure clinical trial data.

---

## **📊 Data Flow**
1. **Fetch raw trial data** from **ClinicalTrials.gov**.
2. [**Identify**](src/services/identifier.py) the atomic eligibility criteria in the selected trials.
3. [**Structure criteria**](src/services/logical_structurizer.py) using logical operators (`AND`, `OR`, etc.).
4. **Store results** as structured **JSON files** in [`output/`](output/) subdirectory for further use.

---

## **💡 Future Plans**
- 🔹 Add **automated patient-trial matching**.
- 🔹 Implement **an API** to allow external applications to query structured trial data.
- 🔹 Optimize **logical structuring** for better accuracy.

---

## **🤝 Contributions**
Contributions are welcome! Please open an issue or submit a pull request.

---

## **📜 License**
This project is licensed under the **MIT License**.

---
