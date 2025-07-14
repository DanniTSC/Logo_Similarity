import csv

IN_CSV = "data/failed_diagnostics.csv"
OUT_CSV = "data/failed_browser_accessible.csv"

def filter_browser_accessible():
    rows = []
    with open(IN_CSV, newline='', encoding='utf-8') as fin:
        reader = csv.DictReader(fin)
        for row in reader:
            if row["browser_accessible"].lower() in {"yes", "maybe"}:
                rows.append(row) #adds the rows that are yes or maybe 

    #output csv with the filtered results 
    with open(OUT_CSV, "w", newline='', encoding='utf-8') as fout:
        writer = csv.DictWriter(fout, fieldnames=reader.fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)
    print(f"[INFO] {len(rows)} domenii browser-accessibile salvate în {OUT_CSV}")

if __name__ == "__main__":
    filter_browser_accessible()


# Script for listing browser-accessible failed domains:
# Generates a list of failed domains that are still accessible via browser. In other words, it tells you which sites are worth retrying with browser-based tools like Selenium.