from time import sleep
from typing import Optional, Any
from dotenv import load_dotenv, find_dotenv
import os
import openai
import json
from sympy import true
import tiktoken
from prompts import booleanPrompt, MQLPrompt, fixJSONPrompt, BackgroundPrompt
from termcolor import colored

GPTModel = "gpt-3.5-turbo-16k"
contextLimits: dict[str, int] = {
    "gpt-3.5-turbo": 4095,
    "gpt-3.5-turbo-16k": 16383
}

load_dotenv(find_dotenv())
openai.api_key = os.getenv("OPENAI_API_KEY")


def AskAI(text: str, prompt: Optional[BackgroundPrompt] = None, model: str = GPTModel, temperature: float = 0, maxAttempts: int = 3, verbose: bool = True) -> Optional[str]:
    print("ASKING AI")
    allMessages: list[dict[str, Any]] = []
    if prompt is not None:
        allMessages += prompt.messages
    allMessages.append(formatTextAsMessage(text, role="user"))
    i = 0
    response = None
    tokens = num_tokens_from_messages(allMessages, model)
    if tokens >= contextLimits[model]:
        if verbose:
            print(
                f"Too many tokens ({tokens}) for {model}. Please reduce the number of messages in the prompt.")
    for i in range(maxAttempts):
        try:
            response = openai.ChatCompletion.create(  # ignore
                model=model, messages=allMessages, temperature=temperature)  # ignore
            break
        except openai.error.RateLimitError as e:  # type: ignore
            print(
                f"TOO MANY REQUESTS. waiting and trying again\n OpenAi says {e.wait}")
            sleep(determineWait(maxTries=maxAttempts, waitTime=60, currentTry=i+1))
            continue
        except Exception as e:
            print(f"OpenAi Error: {e}")
            sleep(determineWait(maxTries=maxAttempts, waitTime=60, currentTry=i+1))
            continue

    if i == maxAttempts-1:
        print(f"Failed to get response from AI after {maxAttempts} attempts.")
        return None

    if response["choices"][0]["finish_reason"] == "length":  # type: ignore
        print("Didn't get to finish, might want to try something shorter")

    assert response
    if verbose:
        allMessages.append(formatTextAsMessage(
            extractResponse(response=response), role="assistant"))
        pretty_print_conversation(messages=allMessages)

    return extractResponse(response)


# this function uses the geometric sum formula to calculate how much to wait between attempts while ensuring that by its last attempt it would have tried to wait the max wait, and then one more time after that waiting a full minute
def determineWait(maxTries, waitTime, currentTry, factor=2) -> int:
    initialWait = (waitTime*(1-factor))/(1-factor**maxTries)
    currentWait = initialWait*factor**(currentTry-1)
    return currentWait


def extractResponse(response) -> str:
    return response["choices"][0]["message"]["content"]


def formatTextAsMessage(text: str, role: str = "user", name: Optional[str] = None) -> "dict[str,Any]":
    message: dict[str, str] = {
        "role": role,
        "content": text
    }
    if name:
        message["name"] = name
    return message


def ConvertTextToBool(text: str, model: str = GPTModel, temperature: float = 0, verbose: bool = True) -> Optional[str]:
    print("converting text to bool")
    return AskAI(prompt=booleanPrompt, text=text, model=model, temperature=temperature, verbose=verbose)


def ConvertBoolToMQL(text: str, model: str = GPTModel, temperature: float = 0, verbose: bool = True) -> Optional[str]:
    print("converting bool to MQL")
    return AskAI(prompt=MQLPrompt, text=text, model=model, temperature=temperature, verbose=verbose)


def TranslateTextToMQL(TextEligibility: str, jsonTries: int = 3) -> Any | None:
    criteria = extract_criteria(TextEligibility)
    listFormat: str | None = ConvertTextToBool(TextEligibility)
    if listFormat is None:
        print("Could not convert to list")
        return None
    MQL: str | None = ConvertBoolToMQL(listFormat)
    if MQL is None:
        print("Could not convert to MQL")
        return None
    ProperMQL: Any | None = fixJSON(MQL, jsonTries)
    return ProperMQL


def fixJSON(text: str, tries: int = 3, maxTemperature: float = 1) -> Any | None:
    print("fixing json")
    jsonText = text
    jsonAttempt = None

    try:
        jsonAttempt = json.loads(jsonText)
        print("JSON is valid, does not need fixing")
        return jsonAttempt
    except:
        print("Your json is not valid, attempting to fix it.")

    for i in range(tries):
        temperature: float = i*(maxTemperature/(tries-1))
        assert jsonText
        jsonText = AskAI(prompt=fixJSONPrompt, text=jsonText,
                         temperature=temperature)
        if jsonText is None:
            print(
                f"\n\n\nAttempt {i+1} at a temperature of {temperature} Failed to  correct json. \n\n Attempt resulted in OpenAi failing\n\n\n\n\n")
            continue
        try:
            jsonAttempt = json.loads(jsonText)
            print(
                f"Attempt {i+1} at a temperature of {temperature} succeeded in correcting json. \n\n Attempt resulted in\n\n{jsonText}\n\n\n")
            return jsonAttempt
        except:
            print(
                f"\n\n\nAttempt {i+1} at a temperature of {temperature} Failed to  correct json. \n\n Attempt resulted in\n\n{jsonText}\n\n\nGetting a bit wilder and trying again")

    print(f"\n\n\nFailed to convert to json\n\n")
    return None


def extract_criteria(input_string: str) -> dict[str, Optional[str]]:
    criteria: dict[str, Optional[str]] = {
        "inclusionCriteria": None,
        "exclusionCriteria": None,
        "bothCriteria": None
    }
    # Split the string into two parts based on "Exclusion Criteria:"
    parts = input_string.split("Exclusion Criteria:")

    # Extract the inclusion and exclusion criteria, or set them to None if not present
    if len(parts) == 2:
        criteria["inclusionCriteria"] = parts[0].replace(
            "Inclusion Criteria:", "").strip()
        criteria["exclusionCriteria"] = parts[1].strip()
    elif len(parts) == 1:
        if "Inclusion Criteria:" in parts[0]:
            criteria["inclusionCriteria"] = parts[0].replace(
                "Inclusion Criteria:", "").strip()
            criteria["exclusionCriteria"] = None
        else:
            criteria["inclusionCriteria"] = None
            criteria["exclusionCriteria"] = parts[0].strip()
    else:
        criteria["bothCriteria"] = parts[0].strip()

    # Return the results as a dictionary
    return criteria


def num_tokens_from_messages(messages, model):
    """Return the number of tokens used by a list of messages."""
    try:
        encoding = tiktoken.encoding_for_model(model)
    except KeyError:
        print("Warning: model not found. Using cl100k_base encoding.")
        encoding = tiktoken.get_encoding("cl100k_base")
    if model in {
        "gpt-3.5-turbo-0613",
        "gpt-3.5-turbo-16k-0613",
        "gpt-4-0314",
        "gpt-4-32k-0314",
        "gpt-4-0613",
        "gpt-4-32k-0613",
    }:
        tokens_per_message = 3
        tokens_per_name = 1
    elif model == "gpt-3.5-turbo-0301":
        # every message follows <|start|>{role/name}\n{content}<|end|>\n
        tokens_per_message = 4
        tokens_per_name = -1  # if there's a name, the role is omitted
    elif "gpt-3.5-turbo" in model:
        return num_tokens_from_messages(messages, model="gpt-3.5-turbo-0613")
    elif "gpt-4" in model:
        return num_tokens_from_messages(messages, model="gpt-4-0613")
    else:
        raise NotImplementedError(
            f"""num_tokens_from_messages() is not implemented for model {model}. See https://github.com/openai/openai-python/blob/main/chatml.md for information on how messages are converted to tokens."""
        )
    num_tokens = 0
    for message in messages:
        num_tokens += tokens_per_message
        for key, value in message.items():
            num_tokens += len(encoding.encode(value))
            if key == "name":
                num_tokens += tokens_per_name
    num_tokens += 3  # every reply is primed with <|start|>assistant<|message|>
    return num_tokens


def pretty_print_conversation(messages: "list[dict[str, str]]"):
    print("printing conversation\n\n")
    role_to_color: dict[str, str] = {
        "system": "red",
        "user": "green",
        "assistant": "blue",
        "function": "magenta",
    }

    for message in messages:
        if message["role"] == "system":
            print(
                colored(f"system: {message['content']}\n", role_to_color[message["role"]]))
        elif message["role"] == "user":
            print(
                colored(f"user: {message['content']}\n", role_to_color[message["role"]]))
        elif message["role"] == "assistant" and message.get("function_call"):
            print(colored(
                f"assistant: {message['function_call']}\n", role_to_color[message["role"]]))
        elif message["role"] == "assistant" and not message.get("function_call"):
            print(
                colored(f"assistant: {message['content']}\n", role_to_color[message["role"]]))
        elif message["role"] == "function":
            print(colored(
                f"function ({message['name']}): {message['content']}\n", role_to_color[message["role"]]))


text = """Inclusion Criteria:

* Histologically or pathologically confirmed malignancy (hematologic or solid tumor) that is metastatic or unresectable and for which standard of care therapy does not exist or is no longer effective
* ACT infusion prior to study enrollment (cohorts include ACT with tumor infiltrating lymphocytes \[TIL\], human leukocyte antigen \[HLA\]-class I T cell receptor \[TCR\]-engineered lymphocytes, HLA-class II TCR-engineered lymphocytes, and chimeric antigen receptor \[CAR\]-engineered T cells)
* Prior ACT therapy should be completed, and residual disease documented by either radiographic progression or active disease observed on biopsy (i.e. hematologic or solid tumor malignancy must be deemed active by the treating investigator); the investigator may deem that the disease is active on the basis of a pre-treatment biopsy demonstrating viable tumor cells or clinical progression of disease (i.e. RECIST progression is not required)
* Solid tumor patients must have measurable disease, defined as at least one lesion that can be accurately measured in at least one dimension (longest diameter to be recorded for non-nodal lesions and short axis for nodal lesions) as \>= 20 mm (\>= 2 cm) with conventional techniques or as \>= 15 mm (\>= 1.5 cm) with spiral computed tomography (CT) scan, magnetic resonance imaging (MRI), or calipers by clinical exam

  * Leukemia and non-Hodgkin's lymphoma patients must have measurable disease according to the revised response criteria for malignant lymphoma
* Disease suitable for assessment by pre- and post-biopsies
* There is no limit to the number of lines of prior therapy; prior anti-programmed cell death (PD)-1 or anti-PD-ligand (L)1 therapy and other immunotherapies are allowed
* Prior anti-PD-1 or anti-PD-L1 therapy may not be administered after ACT and before study atezolizumab (MPDL3280A) administration
* All ACT related toxicities resolved to grade 1 with the exception of alopecia, vitiligo and endocrine abnormalities requiring replacement therapy which may be grade 2
* No prior other anti-cancer therapy, including ACT, for 28 days prior to study administration of atezolizumab
* Age \>= 18 years. Because no dosing or adverse event data are currently available on the use of atezolizumab in patients \< 18 years of age, children are excluded from this study, but will be eligible for future pediatric trials
* Eastern Cooperative Oncology Group (ECOG) performance status =\< 2
* Life expectancy of greater than 3 months
* Absolute neutrophil count \>= 1,000/mcL
* Platelets \>= 75,000/mcL (\>= 50,000 for patients with hematologic malignancies)
* Hemoglobin \>= 8 g/dL
* Total bilirubin =\< 1.5 x institutional upper limit of normal (ULN) (however, patients with known Gilbert disease who have serum bilirubin level =\< 3 x ULN may be enrolled)
* Aspartate aminotransferase (AST) (serum glutamic-oxaloacetic transaminase \[SGOT\])/ alanine aminotransferase (ALT) (serum glutamate pyruvate transaminase \[SGPT\]) =\< 3 x ULN (AST and/or ALT =\< 5 x ULN for patients with liver involvement)
* Creatinine clearance \>= 30 mL/min/1.73 m\^2 by Cockcroft-Gault
* International normalized ratio (INR) and activated partial thromboplastin time (aPTT) =\< 1.5 x ULN (this applies only to patients who do not receive therapeutic anticoagulation; patients receiving therapeutic anticoagulation, such as low-molecular-weight heparin or warfarin, should be on a stable dose)
* Administration of atezolizumab may have an adverse effect on pregnancy and poses a risk to the human fetus, including embryo-lethality; women of child-bearing potential and men must agree to use adequate contraception (hormonal or barrier method of birth control; abstinence) prior to study entry, for the duration of study participation, and for 5 months (150 days) after the last dose of study agent; should a woman become pregnant or suspect she is pregnant while she or her partner is participating in this study, she should inform her treating physician immediately
* Ability to understand and the willingness to sign a written informed consent document

Exclusion Criteria:

* Patients who have had chemotherapy or radiotherapy within 4 weeks (6 weeks for nitrosoureas or mitomycin C) prior to entering the study or those who have not recovered from adverse events (other than alopecia) due to agents administered more than 4 weeks earlier; however, the following therapies are allowed:

  * Hormone-replacement therapy or oral contraceptives
  * Herbal therapy \> 1 week prior to cycle 1, day 1 (herbal therapy intended as anticancer therapy must be discontinued at least 1 week prior to cycle 1, day 1)
  * Palliative radiotherapy for bone metastases \> 2 weeks prior to cycle 1, day 1
* Patients who have received prior treatment with anti-CTLA-4 antibody may be enrolled, provided the following requirements are met:

  * \> 6 weeks from the last dose
  * No history of severe immune-related adverse effects from anti-CTLA-4 antibody (National Cancer Institute \[NCI\] Common Terminology Criteria for Adverse Events \[CTCAE\] grade 3 and 4)
* Treatment with any other investigational agent within 4 weeks prior to cycle 1, day 1
* Treatment with systemic immunostimulatory agents (including, but not limited to, interferon \[IFN\]-alpha or interleukin \[IL\]-2) within 6 weeks prior to cycle 1, day 1
* Treatment with systemic immunosuppressive medications (including, but not limited to, prednisone, cyclophosphamide, azathioprine, methotrexate, thalidomide, and anti-tumor necrosis factor \[anti-TNF\] agents) within 2 weeks prior to cycle 1, day 1

  * Patients who have received acute, low dose, systemic immunosuppressant medications (e.g., a one-time dose of dexamethasone for nausea, premedication for a radiologic contrast allergy) may be enrolled
  * The use of inhaled corticosteroids and mineralocorticoids (e.g., fludrocortisone) for patients with orthostatic hypotension or adrenocortical insufficiency is allowed
  * Patients who receive low-dose supplemental corticosteroids for adrenocortical insufficiency are allowed
* Patients taking bisphosphonate therapy for symptomatic hypercalcemia; use of bisphosphonate therapy for other reasons (e.g., bone metastasis or osteoporosis) is allowed
* Patients with known primary central nervous system (CNS) malignancy or symptomatic CNS metastases are excluded, with the following exceptions:

  * Patients with asymptomatic untreated CNS disease may be enrolled, provided all of the following criteria are met:

    * There are no more than 3 lesions, =\< 1 cm in size each
    * Evaluable or measurable disease outside the CNS
    * No metastases to brain stem, midbrain, pons, medulla, cerebellum, or within 10 mm of the optic apparatus (optic nerves and chiasm)
    * No history of intracranial hemorrhage or spinal cord hemorrhage
    * No ongoing requirement for dexamethasone for CNS disease; patients on a stable dose of anticonvulsants are permitted
    * No neurosurgical resection or brain biopsy within 28 days prior to cycle 1, day 1
  * Patients with asymptomatic treated CNS metastases may be enrolled, provided all the criteria listed above are met as well as the following:

    * Radiographic demonstration of improvement upon the completion of CNS directed therapy and no evidence of interim progression between the completion of CNS-directed therapy and the screening radiographic study
    * No stereotactic radiation or whole-brain radiation within 28 days prior to cycle 1, day 1
    * Screening CNS radiographic study \>= 4 weeks from completion of radiotherapy and \>= 2 weeks from discontinuation of corticosteroids
* Known hypersensitivity to Chinese hamster ovary cell products or other recombinant human antibodies
* History of severe allergic, anaphylactic, or other hypersensitivity reactions to chimeric or humanized antibodies or fusion proteins
* Patients with known clinically significant liver disease (have previously tested positive), including active viral, alcoholic, or other hepatitis; cirrhosis; fatty liver; and inherited liver disease

  * Patients with past or resolved hepatitis B infection (defined as having a negative hepatitis B surface antigen \[HBsAg\] test and a positive anti-HBc \[antibody to hepatitis B core antigen\] antibody test) are eligible
  * Patients positive for hepatitis C virus (HCV) antibody are eligible only if polymerase chain reaction (PCR) is negative for HCV ribonucleic acid (RNA)
* History or risk of autoimmune disease that threatens vital organ function, including, but not limited to, systemic lupus erythematosus, inflammatory bowel disease, vascular thrombosis associated with antiphospholipid syndrome, Wegener's granulomatosis, Guillain-Barre syndrome, multiple sclerosis, or glomerulonephritis

  * Patients with a prior history of immune related events to anti-CTLA-4 may be eligible after discussion with the sponsor; however, patients with a history of grade 3 and 4 pulmonary, CNS and renal events attributed to anti-CTLA-4 agents will be excluded
  * Patients with a history of autoimmune hypothyroidism on a stable dose of thyroid replacement hormone may be eligible
  * Patients with controlled type 1 diabetes mellitus on a stable insulin regimen may be eligible
  * Patients with eczema, psoriasis, lichen simplex chronicus of vitiligo with dermatologic manifestations only (e.g., patients with psoriatic arthritis would be excluded) are permitted provided that they meet the following conditions:

    * Patients with psoriasis must have a baseline ophthalmologic exam to rule out ocular manifestations
    * Rash must cover less than 10% of body surface area (BSA)
    * Disease is well controlled at baseline and only requiring low potency topical steroids (e.g., hydrocortisone 2.5%, hydrocortisone butyrate 0.1%, fluocinolone 0.01%, desonide 0.05%, alclometasone dipropionate 0.05%)
    * No acute exacerbations of underlying condition within the last 12 months (not requiring psoralen plus ultraviolet A radiation \[PUVA\], methotrexate, retinoids, biologic agents, oral calcineurin inhibitors; high potency or oral steroids)
* History of idiopathic pulmonary fibrosis, pneumonitis (including drug induced), organizing pneumonia (i.e., bronchiolitis obliterans, cryptogenic organizing pneumonia, etc.), or evidence of active pneumonitis on screening chest computed tomography (CT) scan; history of radiation pneumonitis in the radiation field (fibrosis) is permitted
* Patients with active tuberculosis (TB) are excluded
* Patients requiring treatment with a RANKL inhibitor (e.g. denosumab) who cannot discontinue it before treatment with atezolizumab
* Severe infections within 4 weeks prior to cycle 1, day 1, including, but not limited to, hospitalization for complications of infection, bacteremia, or severe pneumonia
* Signs or symptoms of infection within 2 weeks prior to cycle 1, day 1
* Major surgical procedure within 28 days prior to cycle 1, day 1 or anticipation of need for a major surgical procedure during the course of the study
* Administration of a live, attenuated vaccine within 4 weeks before cycle 1, day 1 or anticipation that such a live, attenuated vaccine will be required during the study and up to 5 months after the last dose of atezolizumab

  * Influenza vaccination should be given during influenza season only (approximately October to March); patients must not receive live, attenuated influenza vaccine within 4 weeks prior to cycle 1, day 1 or at any time during the study
* Uncontrolled intercurrent illness including, but not limited to, ongoing or active infection, symptomatic congestive heart failure, unstable angina pectoris, cardiac arrhythmia, or psychiatric illness/social situations that would limit compliance with study requirements
* Patients who have previously tested positive for human immunodeficiency virus (HIV) are NOT excluded from this study (please note: testing of all patients wishing to enroll is NOT required), but HIV-positive patients must have:

  * A stable regimen of highly active anti-retroviral therapy (HAART)
  * No requirement for concurrent antibiotics or antifungal agents for the prevention of opportunistic infections
  * A CD4 count above 250 cells/mcL and an undetectable HIV viral load on standard PCR-based tests
* Pregnant women are excluded from this study because atezolizumab is PD-L1 blocking agent with the potential for teratogenic or abortifacient effects; because there is an unknown but potential risk for adverse events in nursing infants secondary to treatment of the mother with atezolizumab, breastfeeding should be discontinued if the mother is treated with atezolizumab"""

TranslateTextToMQL(text)
