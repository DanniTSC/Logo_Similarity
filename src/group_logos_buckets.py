import os, csv
from collections import defaultdict, deque
from PIL import Image
import imagehash, numpy as np
from skimage.metrics import structural_similarity as ssim

RAW_DIR   = "data/logos_preprocessed/"
PHASH_THR = 12 #preprocess then gets the hamming distance, lower than threshold
SSIM_THR  = 0.75 #structural similarity index threshold for high similarity, pixel patterns, greater  than threshold

# remove the file extension, the filenames are formatted as domain_subdomain_timestamp, rebuild the domain, ignoring the timestamp, 
def filename_to_domain(fname):
    base = os.path.splitext(fname)[0]
    parts = base.split("_")
    
    return ".".join(parts[:-1])

#load all .png images from the directory
def load_images():
    return [f for f in os.listdir(RAW_DIR) if f.endswith(".png")]

#compute the perceptual hash pHash for an image file
def calc_phash(path):
    return imagehash.phash(Image.open(path))

#compute structural similarity index between two images
def calc_ssim(a,b):
    img1 = np.array(Image.open(a))
    img2 = np.array(Image.open(b))
    return ssim(img1, img2)


#clustering 

def build_similarity_graph(filenames):
    # 1 compute pHash for all images
    phashes = [calc_phash(os.path.join(RAW_DIR,f)) for f in filenames]
    graph = defaultdict(set)
    buckets = defaultdict(list)
     # 2 Create “buckets” based on the first 8 hex chars of the pHash
    # this drastically reduces the number of pairwise comparisons we need to make, gets the complexity lower, comparing every pair is infeasbile
    for i,h in enumerate(phashes):
        buckets[str(h)[:8]].append(i)

    # 3 for each bucket, compare all images within the bucket pairwise
    for bucket in buckets.values():
        for i in bucket:
            for j in bucket:
                if j <= i: continue #avoid duplicate and self-comparison
                # 4 if the pHash distance is less than threshold, check further
                if phashes[i] - phashes[j] <= PHASH_THR:
                    p1 = os.path.join(RAW_DIR, filenames[i])
                    p2 = os.path.join(RAW_DIR, filenames[j])
                    # 5 if SSIM also high enough, consider images visually similar
                    if calc_ssim(p1, p2) >= SSIM_THR:
                        graph[i].add(j)
                        graph[j].add(i)
    return graph

def connected_components(graph, N):
    # finds all clusters in the similarity graph
    seen, comps = set(), []
    from collections import deque
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

   #write out the results: each row is a cluster, listing all domains in that cluster
    with open("groups.csv","w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["group_id","domains"])
        for gid, comp in enumerate(comps, 1):
            domains = [ filename_to_domain(filenames[i]) for i in comp ]
            w.writerow([gid, ";".join(domains)])

    print(f"→ Wrote {len(comps)} groups to groups.csv")

if __name__=="__main__":
    main() 