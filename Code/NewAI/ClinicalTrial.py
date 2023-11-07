from AI import Ai
from prompts import prepPrompts


class ClinicalTrial:
    def __init__(self, rawText):

        ai = Ai(verbose=False, temperature=0,
                systemMessage=prepPrompts.getToLowerCasePrompt())
        ai.AskAI(rawText.lower())
        ai.pretty_print_conversation()


tester = ClinicalTrial(
    """Inclusion Criteria:\n\n* PHASE II INCLUSION CRITERIA (COMPLETE AS OF 20-MAR-2020)\n* Pathologically (histologically or cytologically) proven diagnosis of head and neck squamous cell carcinoma (HNSCC) involving the oral cavity (excluding lips), oropharynx (p16 negative), larynx, or hypopharynx\n* Patients must have undergone gross total surgical resection of high-risk oral cavity, oropharynx (p16 negative), larynx, or hypopharynx within 63 days prior to registration; Note: patients may have biopsy under general anesthesia in an operating room followed by definitive ablative cancer surgery representing gross total resection; the gross total resection has to be done within 63 days prior to registration; if, however, patients have ablative resection but shortly recur or are determined to have persisting disease requiring re-resection to achieve gross total resection, then the patient is not eligible\n* Patients must have at least 1 of the following high-risk pathologic features: extracapsular nodal extension or invasive cancer at the primary tumor resection margin (tumor on ink)\n* Pathologic stage III or IV HNSCC, including no distant metastases, based upon the following minimum diagnostic workup:\n\n  * General history and physical examination by a radiation oncologist and/or medical oncologist within 84 days prior to registration;\n  * Examination by an ear nose throat (ENT) or head \\& neck surgeon prior to surgery; a laryngopharyngoscopy (mirror and/or fiber optic and/or direct procedure), if appropriate, is recommended but not required; intra-operative examination is acceptable documentation\n  * Pre-operative (op) Imaging of the head and neck: A neck computed tomography (CT) (with contrast) or CT/positron emission tomography (PET) (with contrast) and/or an magnetic resonance imaging (MRI) of the neck (T1 with gadolinium and T2) within 84 days prior to surgery; Note: this imaging data (diagnostic pre-operative scan showing gross disease) is to be submitted in Digital Imaging and Communications in Medicine (DICOM) format via TRIAD; the report is to be uploaded into Rave\n  * Chest CT scan (with or without contrast) or CT/PET that includes the chest (with or without contrast) either within 84 days prior to surgery or within 120 days prior to registration; Note: if the CT/PET with or without contrast is done within 84 days prior to surgery, it fulfills the chest imaging requirement\n* Zubrod performance status of 0-1 within 14 days prior to registration\n* Age \\>= 18\n* Absolute granulocyte count (AGC) \\>= 1,500 cells/mm\\^3 (obtained within 14 days prior to registration on study)\n* Platelets \\>= 100,000 cells/mm\\^3 (obtained within 14 days prior to registration on study)\n* Hemoglobin \\>= 8.0 g/dl (Note: the use of transfusion or other intervention to achieve hemoglobin \\[Hgb\\] \\>= 8.0 g/dl is acceptable)\n* Total bilirubin \\< 2 x institutional upper limit of normal (ULN) within 14 days prior to registration\n* Aspartate aminotransferase (AST) or alanine aminotransferase (ALT) \\< 3 x institutional ULN within 14 days prior to registration\n* Serum creatinine institutional ULN within 14 days prior to registration or; creatinine clearance (CC) \\>= 50 ml/min within 14 days prior to registration determined by 24-hour collection or estimated by Cockcroft-Gault formula\n* Negative urine or serum pregnancy test within 14 days prior to registration for women of childbearing potential\n* The following assessments are required within 14 days prior to registration: sodium (Na), potassium (K), chloride (Cl), glucose, calcium (Ca), magnesium (Mg), and albumin; Note: patients with an initial magnesium \\< 0.5 mmol/L (1.2 mg/dl) may receive corrective magnesium supplementation but should continue to receive either prophylactic weekly infusion of magnesium and/or oral magnesium supplementation (e.g., magnesium oxide) at the investigator's discretion\n* Patients with feeding tubes are eligible for the study\n* Women of childbearing potential and male participants who are sexually active must agree to use a medically effective means of birth control\n* Patient must provide study specific informed consent prior to study entry, including consent for mandatory tissue submission for epidermal growth factor receptor (EGFR) analysis and for oropharyngeal cancer patients, human papilloma virus (HPV) analysis\n* PHASE III: Pathologically (histologically or cytologically) proven diagnosis of head and neck squamous cell carcinoma (HNSCC) involving the oral cavity (excluding lips), oropharynx (p16 negative), larynx, or hypopharynx\n* PHASE III: Patients with oropharyngeal cancer must have p16-negative based on central review prior to Step 2 registration; all patients with oropharyngeal primary must consent for mandatory tissue submission for central p16 confirmation\n* PHASE III: Patients must have undergone gross total surgical resection of high-risk oral cavity, oropharynx (p16 negative), larynx, or hypopharynx within 63 days prior to registration; note: patients may have biopsy under general anesthesia in an operating room followed by definitive ablative cancer surgery representing gross total resection; the gross total resection has to be done within 63 days prior to registration; if, however, patients have ablative resection but shortly recur or are determined to have persisting disease requiring re-resection to achieve gross total resection, then the patient is not eligible\n* PHASE III: Patients must have at least 1 of the following high-risk pathologic features: extracapsular nodal extension or invasive cancer at the primary tumor resection margin (tumor on ink or tumor in a final separately submitted margin)\n* PHASE III: Pathologic stage III or IV HNSCC (American Joint Committee on Cancer \\[AJCC\\] 7th edition), including no distant metastases, based upon the following minimum diagnostic workup:\n\n  * General history and physical examination by a radiation oncologist or medical oncologist within 84 days prior to registration;\n  * Examination by an ENT or head \\& neck surgeon prior to surgery; a laryngopharyngoscopy (mirror or fiberoptic or direct procedure), if appropriate, is recommended but not required. Intra-operative examination is acceptable documentation.\n  * Pre-op Imaging of the head and neck: A neck CT (with contrast and of diagnostic quality) or PET/CT (with contrast and of diagnostic quality) and/or an MRI of the neck of diagnostic quality (T1 with gadolinium and T2) within 84 days prior to surgery; Note: this imaging data (diagnostic pre-operative scan showing gross disease) is to be submitted in DICOM format via TRIAD. The report is to be uploaded into Rave.\n  * Chest CT scan (with or without contrast) or PET/CT that includes the chest (with or without contrast) either within 84 days prior to surgery or within 120 days prior to registration; Note: If the PET/CT with or without contrast is done within 84 days prior to surgery, it fulfills the chest imaging requirement\n* PHASE III: Zubrod performance status of 0-1 within 14 days prior to registration\n* PHASE III: Leukocytes \\>= 2,500 cells/mm\\^3 (obtained within 14 days prior to registration on study)\n* PHASE III: Absolute neutrophil count (ANC) \\>= 1,500 cells/mm\\^3 (obtained within 14 days prior to registration on study)\n* PHASE III: Platelets \\>= 100,000 cells/mm\\^3 (obtained within 14 days prior to registration on study)\n* PHASE III: Hemoglobin \\>= 8.0 g/dL (Note: The use of transfusion or other intervention to achieve Hgb \\>= 8.0 g/dL is acceptable) (obtained within 14 days prior to registration on study)\n* PHASE III: Total bilirubin =\\< 1.5 x institutional upper limit of normal (ULN) (however, patients with known Gilbert disease who have serum bilirubin level =\\< 3 x institutional ULN may be enrolled) (within 14 days prior to registration)\n* PHASE III: AST or ALT =\\< 3 x institutional ULN (within 14 days prior to registration)\n* PHASE III: Alkaline phosphatase =\\< 2.5 x institutional ULN (within 14 days prior to registration)\n* PHASE III: Creatinine clearance (CrCl) \\>= 50 mL/min within 14 days prior to registration determined by 24-hour collection or estimated by Cockcroft-Gault formula\n* PHASE III: Patients with feeding tubes are eligible for the study\n* PHASE III: Negative urine or serum pregnancy test within 14 days prior to registration for women of childbearing potential\n* PHASE III: All patients must provide study specific informed consent prior to study entry\n* PHASE III: Patients positive for human immunodeficiency virus (HIV) are allowed on study, but HIV-positive patients must have:\n\n  * A stable regimen of highly active anti-retroviral therapy (HAART);\n  * No requirement for concurrent antibiotics or antifungal agents for the prevention of opportunistic infections;\n  * A CD4 count above 250 cells/mcL and an undetectable HIV viral load on standard polymerase chain reaction (PCR)-based tests\n\nExclusion Criteria:\n\n* PHASE II EXCLUSION CRITERIA (COMPLETE AS OF 20-MAR-2020)\n* Prior invasive malignancy (except non-melanomatous skin cancer) unless disease free for a minimum of 1095 days (3 years); noninvasive cancers (for example, carcinoma in situ of the breast, oral cavity, or cervix are all permissible) are permitted even if diagnosed and treated \\< 3 years ago\n* Patients with simultaneous primaries or bilateral tumors are excluded, with the exception of patients with bilateral tonsil cancers or patients with T1-2, N0, M0 resected differentiated thyroid carcinoma, who are eligible\n* Prior systemic chemotherapy or anti-epidermal growth factor (EGF) therapy for the study cancer; note that prior chemotherapy for a different cancer is allowable\n* Prior radiotherapy to the region of the study cancer that would result in overlap of radiation therapy fields\n* Severe, active co-morbidity, defined as follows:\n\n  * Unstable angina and/or congestive heart failure requiring hospitalization within 6 months prior to registration\n  * Transmural myocardial infarction within 6 months prior to registration\n  * Acute bacterial or fungal infection requiring intravenous antibiotics at the time of registration\n  * Chronic obstructive pulmonary disease exacerbation or other respiratory illness requiring hospitalization or precluding study therapy at the time of registration\n\n    * Idiopathic pulmonary fibrosis or other severe interstitial lung disease that requires oxygen therapy or is thought to require oxygen therapy within 1 year prior to registration\n  * Hepatic insufficiency resulting in clinical jaundice and/or coagulation defects; note, however, that laboratory tests for coagulation parameters are not required for entry into this protocol\n\n    * Acquired immune deficiency syndrome (AIDS) based upon current Centers for Disease and Control and Prevention (CDC) definition; note: human immunodeficiency virus (HIV) testing is not required for entry into this protocol; the need to exclude patients with AIDS from this protocol is necessary because the treatments involved in this protocol may be significantly immunosuppressive; protocol-specific requirements may also exclude immuno-compromised patients.\n* Grade 3-4 electrolyte abnormalities (Common Terminology Criteria for Adverse Events \\[CTCAE\\], version \\[v.\\] 4):\n* Serum calcium (ionized or adjusted for albumin) \\< 7 mg/dl (1.75 mmol/L) or \\> 12.5 mg/dl (\\> 3.1 mmol/L) despite intervention to normalize levels\n* Glucose \\< 40 mg/dl (\\< 2.2 mmol/L) or \\> 250 mg/dl (\\> 14 mmol/L)\n* Magnesium \\< 0.9 mg/dl (\\< 0.4 mmol/L) or \\> 3 mg/dl (\\> 1.23 mmol/L) despite intervention to normalize levels\n* Potassium \\< 3.0 mmol/L or \\> 6 mmol/L despite intervention to normalize levels\n* Sodium \\< 130 mmol/L or \\> 155 mmol/L despite intervention to normalize levels\n* Pregnancy or women of childbearing potential and men who are sexually active and not willing/able to use medically acceptable forms of contraception; this exclusion is necessary because the treatment involved in this study may be significantly teratogenic\n* Prior allergic reaction to cetuximab\n* PHASE III: Prior invasive malignancy (except non-melanomatous skin cancer) unless disease free for a minimum of 1095 days (3 years) with the following exceptions: T1-2, N0, M0 resected differentiated thyroid carcinoma; Note that noninvasive cancers (For example, carcinoma in situ of the breast, oral cavity, or cervix) are permitted even if diagnosed and treated \\< 3 years ago\n* PHASE III: Patients with simultaneous primaries or bilateral tumors are excluded, with the exception of patients with bilateral tonsil cancers or patients with T1-2, N0, M0 resected differentiated thyroid carcinoma, who are eligible\n* PHASE III: Prior systemic therapy, including cytotoxic chemotherapy, biologic/targeted therapy (such as anti-EGF therapy), or immune therapy for the study cancer; note that prior chemotherapy for a different cancer is allowable, however, a prior anti-PD-1, anti-PD-L1, or anti-PD-L2 agent is not permitted\n* PHASE III: Prior radiotherapy to the region of the study cancer that would result in overlap of radiation therapy fields\n* PHASE III: Severe, active co-morbidity, defined as follows:\n\n  * Patients with known history or current symptoms of cardiac disease, or history of treatment with cardiotoxic agents, should have a clinical risk assessment of cardiac function using the New York Heart Association Functional Classification; to be eligible for this trial, patients should be class 2B or better within 6 months prior to registration\n  * Transmural myocardial infarction within 6 months prior to registration;\n  * Severe infections within 4 weeks prior to registration including, but not limited to, hospitalization for complications of infection, bacteremia, or severe pneumonia;\n  * Acute bacterial or fungal infection requiring intravenous antibiotics at the time of registration; Note: Patients receiving prophylactic antibiotics (e.g., for prevention of a urinary tract infection or chronic obstructive pulmonary disease exacerbation) are eligible.\n  * Chronic obstructive pulmonary disease exacerbation or other respiratory illness requiring hospitalization or precluding study therapy at the time of registration;\n  * History of idiopathic pulmonary fibrosis, pneumonitis (including drug induced), organizing pneumonia (i.e., bronchiolitis obliterans, cryptogenic organizing pneumonia, etc.), or evidence of active pneumonitis on screening chest computed tomography (CT) scan. History of radiation pneumonitis in a prior radiation field (fibrosis) is permitted, provided that field does not overlap with the planned radiation field for the study cancer;\n  * Patients with active tuberculosis (TB) are excluded;\n  * Known clinically significant liver disease, including active viral, alcoholic, or other hepatitis; cirrhosis; fatty liver; and inherited liver disease;\n\n    * Patients with past or resolved hepatitis B infection (defined as having a negative hepatitis B surface antigen \\[HBsAg\\] test and a positive anti-HBc \\[antibody to hepatitis B core antigen\\] antibody test) are eligible.\n    * Patients positive for hepatitis C virus (HCV) antibody are eligible only if polymerase chain reaction (PCR) is negative for HCV RNA.\n  * History of allogeneic bone marrow transplantation or solid organ transplantation.\n  * A diagnosis of immunodeficiency:\n\n    * Acquired immune deficiency syndrome (AIDS) based upon current CDC definition; note: HIV testing is not required for entry into this protocol; the need to exclude patients with AIDS from this protocol is necessary because the treatments involved in this protocol may be significantly immunosuppressive.\n  * Is receiving treatment with systemic immunosuppressive medications (including, but not limited to, prednisone, cyclophosphamide, azathioprine, methotrexate, thalidomide, and anti-tumor necrosis factor \\[anti-TNF\\] agents) within 2 weeks prior to registration.\n\n    * Note: Patients who have received acute, low dose, systemic immunosuppressant medications (e.g., a one-time dose of dexamethasone for nausea) may be enrolled.\n    * Note: The use of inhaled corticosteroids and mineralocorticoids (e.g., fludrocortisone) for patients with orthostatic hypotension or adrenocortical insufficiency is allowed.\n  * History or risk of autoimmune disease, including, but not limited to, systemic lupus erythematosus, rheumatoid arthritis, inflammatory bowel disease, vascular thrombosis associated with antiphospholipid syndrome, Wegener's granulomatosis, Sjogren's syndrome, Guillain-Barr\u00e9 syndrome, multiple sclerosis, vasculitis, or glomerulonephritis.\n\n    * Patients with a history of autoimmune hypothyroidism who are asymptomatic and/or are on a stable dose of thyroid replacement hormone are eligible.\n    * Patients with controlled Type 1 diabetes mellitus on a stable insulin regimen are eligible.\n    * Patients with eczema, psoriasis, lichen simplex chronicus, or vitiligo with dermatologic manifestations only (e.g., patients with psoriatic arthritis would be excluded) are permitted provided that they meet the following conditions:\n    * Patients with psoriasis must have a baseline ophthalmologic exam to rule out ocular manifestations\n    * Rash must cover less than 10% of body surface area (BSA)\n    * Disease is well controlled at baseline and only requiring low potency topical steroids (e.g., hydrocortisone 2.5%, hydrocortisone butyrate 0.1%, flucinolone 0.01%, desonide 0.05%, aclometasone dipropionate 0.05%)\n    * No acute exacerbations of underlying condition within the last 12 months (not requiring psoralen plus ultraviolet A radiation \\[PUVA\\], methotrexate, retinoids, biologic agents, oral calcineurin inhibitors; high potency or oral steroids)\n* PHASE III: Grade 3-4 electrolyte abnormalities (CTCAE, v. 4) within 14 days prior to registration:\n\n  * Serum calcium (ionized or adjusted for albumin) \\< 7 mg/dL (1.75 mmol/L) or \\> 12.5 mg/dL (\\> 3.1 mmol/L) despite intervention to normalize levels;\n  * Glucose \\< 40 mg/dL (\\< 2.2 mmol/L) or \\> 250 mg/dL (\\> 14 mmol/L);\n  * Magnesium \\< 0.9 mg/dL (\\< 0.4 mmol/L) or \\> 3 mg/dL (\\> 1.23 mmol/L) despite intervention to normalize levels;\n  * Potassium \\< 3.0 mmol/L or \\> 6 mmol/L despite intervention to normalize levels;\n  * Sodium \\< 130 mmol/L or \\> 155 mmol/L despite intervention to normalize levels.\n* PHASE III: Pregnancy or women of childbearing potential and men who are sexually active and not willing/able to use medically acceptable forms of contraception for up to 5 months from last study treatment; this exclusion is necessary because the treatment involved in this study may be significantly teratogenic. Women who are breastfeeding and unwilling to discontinue are also excluded\n* PHASE III: History of severe allergic, anaphylactic, or other hypersensitivity reactions to chimeric or humanized antibodies or fusion proteins\n* PHASE III: Patients taking bisphosphonate therapy for symptomatic hypercalcemia. Use of bisphosphonate therapy for other non-oncologic reasons (e.g., osteoporosis) is allowed\n* PHASE III: Patients requiring treatment with a RANKL inhibitor (e.g. denosumab) for non-oncologic reasons who cannot discontinue it before registration\n* PHASE III: Patients with known distant metastatic disease are excluded\n* PHASE III: Known hypersensitivity to Chinese hamster ovary cell products or other recombinant human antibodies\n* PHASE III: Major surgical procedure within 28 days prior to registration or anticipation of need for a major surgical procedure during the course of the study\n* PHASE III: Administration of a live, attenuated vaccine within 4 weeks prior to registration or anticipation that such a live, attenuated vaccine will be required during the study and for patients receiving atezolizumab, up to 5 months after the last dose of atezolizumab.\n\n  * Influenza vaccination should be given during influenza season only (approximately October to March). Patients must not r""")
