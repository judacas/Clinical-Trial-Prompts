import pandas as pd

# Read the CSV file
df = pd.read_csv("us_trials_nct_numbers.csv")

# Sample 1000 random rows
sampled_df = df.sample(n=1000, random_state=1)

# Save to new CSV
sampled_df.to_csv("1k_random_from_us_trials_nct_numbers.csv", index=False)
