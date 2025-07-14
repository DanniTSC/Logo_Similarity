import pandas as pd

def create_debug_subset():

    parquet_path = "data/logos.snappy.parquet"
    output_csv   = "data/subset100.csv"
    sample_size  = 100

#read parquet
    df = pd.read_parquet(parquet_path, engine="pyarrow")

 #validate the existance of the domain column and drop duplicates or NaN
    if "domain" not in df.columns:
        raise KeyError("Expected a 'domain' column in the Parquet file.")
    df = df[["domain"]].dropna().drop_duplicates()

    #42, the generator seed to always get the same data
    subset = df.sample(n=sample_size, random_state=42).reset_index(drop=True)
    #drop the index and reset it to start from 0

#write subset as csv
    subset.to_csv(output_csv, index=False)

    print(f"[INFO] Created debug subset with {len(subset)} domains → {output_csv}")

if __name__ == "__main__":
    create_debug_subset()

    #Script to create subsets from the large Parquet file
# Used to split the full dataset into smaller, manageable batches (CSV format)
