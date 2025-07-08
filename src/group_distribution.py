import pandas as pd

groups_df = pd.read_csv("groups_wo_buckets.csv")

groups_df["num_domains"] = groups_df["domains"].apply(lambda x: len(x.split(";")))
group_sizes = groups_df["num_domains"].value_counts().sort_index()

print("Distribuția clară a grupurilor după numărul de domenii:")
print(group_sizes)

# clarifică și câte domenii unice ai
num_unique_domains = (groups_df["num_domains"] == 1).sum()
total_domains = groups_df["num_domains"].sum()

print(f"\nAi {num_unique_domains} domenii unice (fără grup).")
print(f"Total domenii grupate: {total_domains}")
