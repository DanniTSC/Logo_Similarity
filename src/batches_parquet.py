import pandas as pd
import os

PARQUET_FILE = "data\logos.snappy.parquet"
BATCH_SIZE = 150
BATCHES_DIR = "batches/"

def split_parquet_to_batches():
    os.makedirs(BATCHES_DIR, exist_ok=True)
    df = pd.read_parquet(PARQUET_FILE)
    domains = df['domain'].drop_duplicates().reset_index(drop=True)
    total = len(domains)
    # iterate through the domains list in steps of BATCH_SIZE
    for i in range(0, total, BATCH_SIZE):
        # slice out the next batch of domains
        batch = domains.iloc[i:i+BATCH_SIZE]
        # build the filename for this batch and save it as csv
        batch_csv = os.path.join(BATCHES_DIR, f"batch_{i//BATCH_SIZE+1:03d}.csv")
        batch.to_frame(name="domain").to_csv(batch_csv, index=False)
        print(f"Written: {batch_csv} ({len(batch)} domains)")

if __name__ == "__main__":
    split_parquet_to_batches()

#Script for splitting the large Parquet file:
#Used to break the big Parquet file into smaller CSV batches, so I can process, validate, or debug the data more easily, piece by piece.
