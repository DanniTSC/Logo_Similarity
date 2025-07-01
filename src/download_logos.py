#!/usr/bin/env python3
"""
Purpose:
  Extract and download logos for a fixed subset of domains,
  handling SVG inline, deduplicating, brand homepage fallback,
  and logging all errors and heuristics.
  No cairosvg! SVG saved as-is, hash is on SVG or PNG bytes.
"""

import os
import csv
import time
import requests
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup
from pathlib import Path
import hashlib

# === Configuration ===
SUBSET_CSV    = "data/subset25random.csv"
OUTPUT_DIR    = "data/logos/"
LOG_CSV       = "data/extraction_log.csv"
HTTP_TIMEOUT  = 8
MAX_RETRIES   = 2
USER_AGENT    = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36"

def ensure_dirs():
    Path(OUTPUT_DIR).mkdir(parents=True, exist_ok=True)
    Path(os.path.dirname(LOG_CSV)).mkdir(parents=True, exist_ok=True)

def load_and_clean_domains():
    seen = set()
    cleaned = []
    with open(SUBSET_CSV, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        if "domain" not in reader.fieldnames:
            raise KeyError("Expected 'domain' column in subset CSV")
        for row in reader:
            raw = row["domain"]
            dom = raw.strip().lower().rstrip(" ,/\\")
            if not dom: continue
            if dom not in seen:
                seen.add(dom)
                cleaned.append(dom)
    return cleaned

def fetch_url(url):
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            resp = requests.get(url, timeout=HTTP_TIMEOUT,
                                headers={"User-Agent": USER_AGENT})
            resp.raise_for_status()
            return resp
        except Exception:
            if attempt < MAX_RETRIES:
                time.sleep(1)
            else:
                raise

def extract_svg_from_html(soup, base, safe_name):
    """
    Detect SVG inline logo, save as .svg (for hash/cluster).
    Returns path to SVG or None.
    """
    # caută SVG inline cu parent “logo” în class/id
    for parent in soup.find_all(['div', 'a', 'span'], class_=lambda x: x and 'logo' in x.lower()):
        svg = parent.find('svg')
        if svg:
            svg_str = str(svg)
            svg_path = os.path.join(OUTPUT_DIR, f"{safe_name}.svg")
            with open(svg_path, "w", encoding="utf-8") as f:
                f.write(svg_str)
            return svg_path
    # fallback: svg direct în <header> sau la începutul body
    svg_tag = soup.find('svg')
    if svg_tag:
        svg_str = str(svg_tag)
        svg_path = os.path.join(OUTPUT_DIR, f"{safe_name}.svg")
        with open(svg_path, "w", encoding="utf-8") as f:
            f.write(svg_str)
        return svg_path
    return None

def find_logo_url(domain, fallback_brand_search=True):
    """
    Returns (logo_url, strategy, svg_path)
    strategy = one of ['img-logo', 'link-logo', 'og-image', 'twitter-image', 'svg-inline', 'brand-homepage', 'icon', 'favicon']
    svg_path = path to svg if detected as inline, else None
    """
    base = f"https://{domain}"
    safe = domain.replace(".", "_")
    try:
        resp = fetch_url(base)
    except Exception as e:
        return None, "site-unreachable", None

    soup = BeautifulSoup(resp.text, "html.parser")

    # 1. img-uri cu "logo" în class/id/alt/src, dar nu cu "slider", "banner", "bgimage", "background", "hero"
    imgs = soup.find_all("img", src=True)
    candidates = []
    badwords = ['slider', 'banner', 'bgimage', 'background', 'hero', 'cover', 'mainvisual']
    for img in imgs:
        src = img.get("src", "").lower()
        alt = img.get("alt", "").lower() if img.get("alt") else ""
        cid = " ".join(img.get("class", [])).lower() if img.get("class") else ""
        iid = img.get("id", "").lower() if img.get("id") else ""
        all_fields = [src, alt, cid, iid]
        if any('logo' in f for f in all_fields) and not any(bad in f for bad in badwords for f in all_fields):
            try:
                w = int(img.get("width", 0))
                h = int(img.get("height", 0))
            except:
                w = h = 0
            area = w * h
            candidates.append((area, img["src"]))
    candidates = [c for c in candidates if c[0] > 0]
    if candidates:
        candidates.sort(key=lambda x: x[0])
        return urljoin(base, candidates[0][1]), "img-logo", None
    elif imgs:
        for img in imgs:
            if "logo" in img.get("src", "").lower():
                return urljoin(base, img["src"]), "img-logo", None

    # 2. Inline SVG (cu parent logo)
    svg_path = extract_svg_from_html(soup, base, safe)
    if svg_path:
        return svg_path, "svg-inline", svg_path

    # 3. <link rel="logo">
    logo_link = soup.find("link", rel=lambda x: x and "logo" in x.lower())
    if logo_link and logo_link.get("href"):
        return urljoin(base, logo_link["href"]), "link-logo", None

    # 4. OG image
    og = soup.find("meta", property="og:image")
    if og and og.get("content"):
        return urljoin(base, og["content"]), "og-image", None
    # 5. Twitter image
    tw = soup.find("meta", attrs={"name": "twitter:image"})
    if tw and tw.get("content"):
        return urljoin(base, tw["content"]), "twitter-image", None

    # 6. link icon
    icon = soup.find("link", rel=lambda x: x and "icon" in x.lower())
    if icon and icon.get("href"):
        return urljoin(base, icon["href"]), "icon", None

    # 7. Fallback: favicon și/sau homepage brand-mamă
    fav = urljoin(base, "/favicon.ico")
    if fallback_brand_search:
        brand_links = soup.find_all("a", class_=lambda x: x and ("brand" in x.lower() or "logo" in x.lower()))
        checked = set()
        for link in brand_links:
            href = link.get("href")
            if not href: continue
            abs_url = urljoin(base, href)
            netloc = urlparse(abs_url).netloc
            if netloc and netloc != domain and netloc not in checked:
                checked.add(netloc)
                logo, strat, svg_path = find_logo_url(netloc, fallback_brand_search=False)
                if logo:
                    return logo, f"brand-homepage:{netloc}", svg_path

    return fav, "favicon", None

def save_image_from_url(resp, domain, existing_hashes):
    img_bytes = resp.content
    img_hash = hashlib.md5(img_bytes).hexdigest()
    if img_hash in existing_hashes:
        return existing_hashes[img_hash], img_hash
    timestamp = int(time.time())
    safe = domain.replace(".", "_")
    filename = f"{safe}_{timestamp}.png"
    path = os.path.join(OUTPUT_DIR, filename)
    with open(path, "wb") as f:
        f.write(img_bytes)
    existing_hashes[img_hash] = filename
    return filename, img_hash

def save_svg_from_path(svg_path, domain, existing_hashes):
    with open(svg_path, "rb") as f:
        svg_bytes = f.read()
    svg_hash = hashlib.md5(svg_bytes).hexdigest()
    if svg_hash in existing_hashes:
        return existing_hashes[svg_hash], svg_hash
    timestamp = int(time.time())
    safe = domain.replace(".", "_")
    filename = f"{safe}_{timestamp}.svg"
    dest_path = os.path.join(OUTPUT_DIR, filename)
    with open(dest_path, "wb") as f:
        f.write(svg_bytes)
    existing_hashes[svg_hash] = filename
    return filename, svg_hash

def log_result(domain, logo_url, filename, status, message):
    write_header = not os.path.exists(LOG_CSV)
    with open(LOG_CSV, "a", newline="", encoding="utf-8") as cf:
        writer = csv.writer(cf)
        if write_header:
            writer.writerow(["domain", "logo_url", "filename", "status", "message"])
        writer.writerow([domain, logo_url or "", filename or "", status, message])

def main():
    ensure_dirs()
    domains = load_and_clean_domains()
    total = len(domains)
    success = 0
    existing_hashes = {}
    hash_to_domains = {}
    for domain in domains:
        logo_url = None
        filename = None
        img_hash = None
        svg_path = None
        strategy = None
        try:
            logo_url, strategy, svg_path = find_logo_url(domain)
            if not logo_url:
                raise ValueError("No logo URL found by any strategy")
            if strategy == "svg-inline":
                filename, img_hash = save_svg_from_path(logo_url, domain, existing_hashes)
                message = f"SVG inline extracted. hash={img_hash}"
            elif logo_url.endswith(".svg"):
                resp = fetch_url(logo_url)
                # Save SVG direct
                safe = domain.replace(".", "_")
                svg_path = os.path.join(OUTPUT_DIR, f"{safe}_{int(time.time())}.svg")
                with open(svg_path, "wb") as f:
                    f.write(resp.content)
                filename, img_hash = save_svg_from_path(svg_path, domain, existing_hashes)
                message = f"SVG URL downloaded. hash={img_hash}"
            else:
                resp = fetch_url(logo_url)
                filename, img_hash = save_image_from_url(resp, domain, existing_hashes)
                message = f"Downloaded. hash={img_hash}"
            if img_hash not in hash_to_domains:
                hash_to_domains[img_hash] = []
            hash_to_domains[img_hash].append(domain)
            log_result(domain, logo_url, filename, "success", f"{strategy} | {message}")
            print(f"[SUCCESS] {domain} → {logo_url} [{strategy}] (hash={img_hash})")
            success += 1
        except Exception as e:
            log_result(domain, logo_url, filename, "failure", str(e))
            print(f"[FAILURE] {domain} → {e!r}")

    print("\nGroups of domains with identical logos:")
    for h, dlist in hash_to_domains.items():
        if len(dlist) > 1:
            print(f"Hash {h[:8]}...: {dlist}")
    rate = (success / total) * 100 if total else 0
    print(f"\nProcessed {total} domains: {success} successes, {total-success} failures")
    print(f"Success rate: {rate:.1f}%")

if __name__ == "__main__":
    main()
