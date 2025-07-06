import os
import pandas as pd
from PIL import Image
import imagehash
from skimage.metrics import structural_similarity as ssim
import numpy as np
from itertools import combinations
from collections import defaultdict

LOGOS_DIR = "data/logos/"
HASH_CSV = "data/logo_hashes.csv"

def calculate_phash(image_path):
    img = Image.open(image_path).convert('L').resize((128,128))
    return imagehash.phash(img)

def calculate_ssim(img1_path, img2_path):
    img1 = np.array(Image.open(img1_path).convert('L').resize((128,128)))
    img2 = np.array(Image.open(img2_path).convert('L').resize((128,128)))
    score, _ = ssim(img1, img2, full=True)
    return score

def build_logo_dataframe():
    data = []
    for fname in os.listdir(LOGOS_DIR):
        fpath = os.path.join(LOGOS_DIR, fname)
        phash = calculate_phash(fpath)
        data.append((fname, str(phash)))
    df = pd.DataFrame(data, columns=['filename','phash'])
    df.to_csv(HASH_CSV, index=False)
    return df

def group_by_phash(df, max_hamming_dist=10):
    groups = defaultdict(list)
    assigned = set()
    filenames = df['filename'].tolist()
    hashes = [imagehash.hex_to_hash(h) for h in df['phash']]

    for i, (fname, hash_val) in enumerate(zip(filenames, hashes)):
        if fname in assigned:
            continue
        group_id = fname
        groups[group_id].append(fname)
        assigned.add(fname)

        for j, (fname2, hash_val2) in enumerate(zip(filenames[i+1:], hashes[i+1:])):
            if fname2 in assigned:
                continue
            if hash_val - hash_val2 <= max_hamming_dist:
                groups[group_id].append(fname2)
                assigned.add(fname2)
    return groups

def refine_groups_with_ssim(groups, ssim_threshold=0.75):
    refined_groups = defaultdict(list)
    for group_id, files in groups.items():
        refined = [files[0]]
        base_img = os.path.join(LOGOS_DIR, files[0])
        for fname in files[1:]:
            compare_img = os.path.join(LOGOS_DIR, fname)
            similarity = calculate_ssim(base_img, compare_img)
            if similarity >= ssim_threshold:
                refined.append(fname)
        refined_groups[group_id] = refined
    return refined_groups

def main():
    df = build_logo_dataframe()
    print("Calculat pHash pentru toate logo-urile.")

    initial_groups = group_by_phash(df)
    print(f"Grupuri inițiale formate după pHash: {len(initial_groups)}")

    final_groups = refine_groups_with_ssim(initial_groups)
    print("Grupuri finale rafinate cu SSIM:")

   
    for i, (gid, members) in enumerate(final_groups.items(), 1):
        print(f"Group {i}: {members}")

if __name__ == "__main__":
    main()
