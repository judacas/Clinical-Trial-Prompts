import spacy
from spacy import displacy
from spacy import explain

# Load the language model
nlp = spacy.load("en_core_web_sm")

# Sample text
text = "Patients with biopsy-proven metastatic carcinoid tumors or other neuroendocrine tumors (Islet cell, Gastrinomas, and VIPomas) with at least one measurable lesion (other than bone) that has either not been previously irradiated or if previously irradiated has demonstrated progression since the radiation therapy."

# Process the text
doc = nlp(text)


# Print the dependency parse tree
for token in doc:
    print(f"{token.text} -> {token.head.text} ({token.dep_})")

# Visualize the dependency tree


unique_tags = set()
unique_labels = set()

# Collect dependency tags
for token in doc:
    unique_tags.add(token.dep_)

# Collect named entity labels
for ent in doc.ents:
    unique_labels.add(ent.label_)

# Print explanations for dependency tags
print("\n\nDependency Tags and their explanations:")
for tag in unique_tags:
    print(f"{tag}: {explain(tag)}")

# Print explanations for named entity labels
print("\nNamed Entity Labels and their explanations:")
for label in unique_labels:
    print(f"{label}: {explain(label)}")
displacy.render(doc, style="dep")
displacy.serve(doc, style="dep")