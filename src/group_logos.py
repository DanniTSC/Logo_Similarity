import os, csv
from collections import defaultdict, deque
from PIL import Image
import imagehash
import numpy as np
from skimage.metrics import structural_similarity as ssim

RAW_DIR   = "data/logos_preprocessed/"
PHASH_THR = 12
SSIM_THR  = 0.75

def filename_to_domain(fname):
    base = os.path.splitext(fname)[0]
    parts = base.split("_")
    return ".".join(parts[:-1])

def load_images():
    return [f for f in os.listdir(RAW_DIR) if f.endswith(".png")]

def calc_phash(path):
    return imagehash.phash(Image.open(path))

def calc_ssim(a, b):
    img1 = np.array(Image.open(a))
    img2 = np.array(Image.open(b))
    return ssim(img1, img2)

def build_similarity_graph(filenames):
    phashes = [calc_phash(os.path.join(RAW_DIR, f)) for f in filenames]
    graph = defaultdict(set)
    N = len(filenames)
    for i in range(N):
        for j in range(i + 1, N):
            if phashes[i] - phashes[j] <= PHASH_THR:
                p1 = os.path.join(RAW_DIR, filenames[i])
                p2 = os.path.join(RAW_DIR, filenames[j])
                if calc_ssim(p1, p2) >= SSIM_THR:
                    graph[i].add(j)
                    graph[j].add(i)
    return graph

def connected_components(graph, N):
    seen, comps = set(), []
    for i in range(N):
        if i in seen: continue
        q, comp = deque([i]), []
        while q:
            u = q.popleft()
            if u in seen: continue
            seen.add(u)
            comp.append(u)
            for v in graph[u]:
                if v not in seen:
                    q.append(v)
        comps.append(comp)
    return comps

def main():
    filenames = load_images()
    graph = build_similarity_graph(filenames)
    comps = connected_components(graph, len(filenames))
    with open("groups.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["group_id", "domains"])
        for gid, comp in enumerate(comps, 1):
            domains = [filename_to_domain(filenames[i]) for i in comp]
            w.writerow([gid, ";".join(domains)])

    print(f"→ Wrote {len(comps)} groups to groups.csv")

if __name__ == "__main__":
    main()
