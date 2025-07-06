import os
import csv
import time
import requests
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup
from pathlib import Path
import hashlib
import json

HASHES_FILE = "data/logo_hashes.json"

def load_existing_hashes():
    if os.path.exists(HASHES_FILE):
        if os.stat(HASHES_FILE).st_size == 0:
            # Dacă e gol, scrie {}
            with open(HASHES_FILE, "w", encoding="utf-8") as f:
                f.write("{}")
            return {}
        with open(HASHES_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_existing_hashes(existing_hashes):
    with open(HASHES_FILE, "w", encoding="utf-8") as f:
        json.dump(existing_hashes, f)


# --- Config ---
SUBSET_CSV    = "batches/batch_023.csv"
OUTPUT_DIR    = "data/logos/"
FAILED_CSV    = "data/failed_sites.csv"
HTTP_TIMEOUT  = 8
USER_AGENT    = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko)"

def ensure_dirs():
    Path(OUTPUT_DIR).mkdir(parents=True, exist_ok=True)
    Path(os.path.dirname(FAILED_CSV)).mkdir(parents=True, exist_ok=True)

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

def fetch_url(url, try_http_fallback=True):
    try:
        resp = requests.get(url, timeout=HTTP_TIMEOUT, headers={"User-Agent": USER_AGENT})
        resp.raise_for_status()
        return resp
    except Exception as e:
        if try_http_fallback and url.startswith("https://"):
            http_url = "http://" + url[8:]
            try:
                resp = requests.get(http_url, timeout=HTTP_TIMEOUT, headers={"User-Agent": USER_AGENT})
                resp.raise_for_status()
                return resp
            except Exception:
                pass
        # Returnăm None dacă nu poate fi accesat, nu logăm aici!
        return None

def is_logo_context(el):
    goodwords = ["logo", "header", "nav", "brand", "site-header", "site-logo", "navbar", "main-logo"]
    badwords = ["partner", "footer", "client", "sponsor", "award", "asociat", "carousel"]
    while el and el.name != "body":
        attrs = " ".join([el.get("id", ""), " ".join(el.get("class", []))])
        if any(gw in attrs.lower() for gw in goodwords):
            if not any(bw in attrs.lower() for bw in badwords):
                return True
        el = el.parent
    return False

def extract_svg_logo(soup, safe_name):
    for svg in soup.find_all("svg"):
        if is_logo_context(svg):
            svg_str = str(svg)
            svg_path = os.path.join(OUTPUT_DIR, f"{safe_name}.svg")
            with open(svg_path, "w", encoding="utf-8") as f:
                f.write(svg_str)
            return svg_path
    return None

def find_logo_url(domain, fallback_brand_search=True):
    base = f"https://{domain}"
    safe = domain.replace(".", "_")
    resp = fetch_url(base)
    if resp is None:
        # Nu logăm aici, returnăm "site-unreachable" ca status
        return None, "site-unreachable", None

    soup = BeautifulSoup(resp.text, "html.parser")

    imgs = soup.find_all("img", src=True)
    header_imgs = []
    for img in imgs:
        src = img.get("src", "").lower()
        alt = img.get("alt", "").lower() if img.get("alt") else ""
        cid = " ".join(img.get("class", [])).lower() if img.get("class") else ""
        iid = img.get("id", "").lower() if img.get("id") else ""
        all_fields = [src, alt, cid, iid]
        if any('logo' in f for f in all_fields):
            if is_logo_context(img):
                try:
                    w = int(img.get("width", 0))
                    h = int(img.get("height", 0))
                except:
                    w = h = 0
                area = w * h
                header_imgs.append((area if area > 0 else 99999, img["src"]))
    if header_imgs:
        header_imgs.sort(key=lambda x: x[0])
        return urljoin(base, header_imgs[0][1]), "img-header-logo", None

    svg_path = extract_svg_logo(soup, safe)
    if svg_path:
        return svg_path, "svg-inline-header", svg_path

    logo_link = soup.find("link", rel=lambda x: x and "logo" in x.lower())
    if logo_link and logo_link.get("href"):
        return urljoin(base, logo_link["href"]), "link-logo", None

    og = soup.find("meta", property="og:image")
    if og and og.get("content"):
        return urljoin(base, og["content"]), "og-image", None
    tw = soup.find("meta", attrs={"name": "twitter:image"})
    if tw and tw.get("content"):
        return urljoin(base, tw["content"]), "twitter-image", None

    icon = soup.find("link", rel=lambda x: x and "icon" in x.lower())
    if icon and icon.get("href"):
        try:
            icon_url = urljoin(base, icon["href"])
            resp_icon = fetch_url(icon_url)
            if resp_icon.status_code == 200:
                return icon_url, "icon", None
        except Exception:
            pass

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

    favicon_url = urljoin(base, "/favicon.ico")
    try:
        resp_favicon = fetch_url(favicon_url)
        if resp_favicon.status_code == 200:
            return favicon_url, "favicon", None
    except Exception:
        pass

    return None, "no-logo", None

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

def main():
    ensure_dirs()
    domains = load_and_clean_domains()
    total = len(domains)
    success = 0
    fail = 0
    existing_hashes = load_existing_hashes()

    if not os.path.exists(FAILED_CSV) or os.stat(FAILED_CSV).st_size == 0:
        with open(FAILED_CSV, "w", newline="", encoding="utf-8") as cf:
            writer = csv.writer(cf)
            writer.writerow(["domain", "status", "message"])

    for domain in domains:
        try:
            logo_url, strategy, svg_path = find_logo_url(domain)
            if not logo_url:
                raise ValueError("No logo URL found by any strategy")
            if strategy == "svg-inline-header":
                filename, img_hash = save_svg_from_path(logo_url, domain, existing_hashes)
                message = f"SVG inline extracted. hash={img_hash}"
            elif logo_url.endswith(".svg"):
                resp = fetch_url(logo_url)
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
            print(f"[SUCCESS] {domain} → {logo_url} [{strategy}] (hash={img_hash})")
            success += 1
        except Exception as e:
            print(f"[FAILURE] {domain} → {e!r}")
            with open(FAILED_CSV, "a", newline="", encoding="utf-8") as cf:
                writer = csv.writer(cf)
                writer.writerow([domain, "fail", str(e)])
            fail += 1

    rate = (success / total) * 100 if total else 0
    save_existing_hashes(existing_hashes)
    print(f"\nProcessed {total} domains: {success} successes, {fail} failures")
    print(f"Success rate: {rate:.1f}%")
    print(f"Failures logged in {FAILED_CSV}")

if __name__ == "__main__":
    main()

    #Main script used to download logos
# Core logic that processes domains and extracts logos using multiple strategies