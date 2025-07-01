#!/usr/bin/env python3
"""
Purpose:
  Create a reproducible debug subset of exactly 25 domains from the full Parquet list,
  so downstream steps (logo extraction, preprocessing, etc.) can be developed and tested
  quickly without loading the entire dataset each time.
"""

import pandas as pd

def create_debug_subset():
    # 1. Define fixed paths and parameters
    parquet_path = "data/logos.snappy.parquet"
    output_csv   = "data/subset25.csv"
    sample_size  = 25

    # 2. Load the full list of domains from Parquet
    #    Using pyarrow engine for fast I/O
    df = pd.read_parquet(parquet_path, engine="pyarrow")

    # 3. Minimal cleaning: ensure we have a 'domain' column, drop nulls & duplicates
    if "domain" not in df.columns:
        raise KeyError("Expected a 'domain' column in the Parquet file.")
    df = df[["domain"]].dropna().drop_duplicates()
    # Purpose: guarantee the subset contains only valid, unique domain entries

    # 4. Sample exactly 25 domains, using a fixed random seed for reproducibility
    subset = df.sample(n=sample_size, random_state=42).reset_index(drop=True)
    # Purpose: get a small, stable subset so tests always run on the same data

    # 5. Write the subset to CSV for downstream modules to consume
    subset.to_csv(output_csv, index=False)
    # Purpose: persist the subset so logo-extraction scripts can pick it up without re-running sampling

    print(f"[INFO] Created debug subset with {len(subset)} domains → {output_csv}")

if __name__ == "__main__":
    create_debug_subset()
