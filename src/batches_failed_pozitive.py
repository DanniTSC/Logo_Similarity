import pandas as pd
import os
import glob
import random

BATCHES_DIR = "batches/"
OUTPUT_DIR = "batches_review/"
N_PER_BATCH = 5  

def sample_from_each_batch():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
     # find all CSV batch files in the batches dir, sorted alphabetically
    batch_files = sorted(glob.glob(os.path.join(BATCHES_DIR, "batch_*.csv")))
    total_sampled = 0
    for batch in batch_files:
        df = pd.read_csv(batch)
        # Read each batch as a DataFrame and take 5
        sampled = df.sample(min(N_PER_BATCH, len(df)), random_state=42)
        out_csv = os.path.join(OUTPUT_DIR, os.path.basename(batch))
        sampled.to_csv(out_csv, index=False)
        print(f"Sampled {len(sampled)} from {os.path.basename(batch)}")
        total_sampled += len(sampled)
    print(f"\nTotal domenii eșantionate: {total_sampled}")

if __name__ == "__main__":
    sample_from_each_batch()

#Script for detecting false positives:
#Used to take a small but representative sample from all extracted batches (from the large Parquet file), run the script on this subset, and manually check for any false positives among the extracted logos.



