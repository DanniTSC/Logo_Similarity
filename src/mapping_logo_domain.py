import os
import pandas as pd

LOGOS_DIR = "data/logos/"
OUTPUT_CSV = "data/domain_logo_mapping.csv"

def map_domains_to_logos():
    data = []
    for fname in os.listdir(LOGOS_DIR):
        
        domain_parts = fname.split("_")[:-1]  
        domain = ".".join(domain_parts).replace("_", ".").replace("..", ".")
        data.append({"domain": domain, "filename": fname})

    df = pd.DataFrame(data)
    df.to_csv(OUTPUT_CSV, index=False)
    print(f"Mapping creat clar în {OUTPUT_CSV}")

if __name__ == "__main__":
    map_domains_to_logos()
