import os
import csv
import hashlib
import time
from urllib.parse import urljoin
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright
from pathlib import Path

# --- Config ---
INPUT_CSV    = "data/failed_diagnostics.csv"
OUTPUT_DIR   = "data/logo_extraction_browser_accessible.csv/"
RESULTS_CSV  = "data/results_playwright.csv"

# --- Setup ---
Path(OUTPUT_DIR).mkdir(parents=True, exist_ok=True)

def is_logo_context(el):
    good = ["logo", "header", "nav", "brand", "site-header", "site-logo"]
    bad  = ["partner", "footer", "client", "sponsor", "carousel"]
    #walk the DOM until I hit the body tag
    while el and el.name != "body":
        # collect id and class attributes, lowercased, for keyword checking
        attrs = " ".join([el.get("id",""), " ".join(el.get("class",[]))]).lower()
        #it's likely a logo context
        if any(g in attrs for g in good) and not any(b in attrs for b in bad):
            return True
        el = el.parent #check the parent header, anv etc
    return False

def extract_logo(soup, base_url):
    #all img tags with src attribute
    imgs = soup.find_all("img", src=True)
    header_imgs = []
    for img in imgs:
        #combine everythin to search for logo keyword
        attrs = " ".join([img.get("alt",""), " ".join(img.get("class",[])), img.get("id","")]).lower()
        if "logo" in attrs and is_logo_context(img):
            src = urljoin(base_url, img["src"])
            header_imgs.append(src)
    if header_imgs:
        #return first logo candidate
        return header_imgs[0]

    # no image find inline svgs
    svgs = soup.find_all("svg")
    for svg in svgs:
        if is_logo_context(svg):
            svg_str = str(svg)
            return "inline_svg", svg_str

    # favicon fallback
    favicon = soup.find("link", rel=lambda x: x and "icon" in x.lower())
    if favicon and favicon.get("href"):
        return urljoin(base_url, favicon["href"])

    return None

def save_logo(content, domain, ext):
    hash_md5 = hashlib.md5(content).hexdigest()
      #build the filename using domain and hash to avoid name collisions and deduplicate
    filename = f"{domain}_{hash_md5}.{ext}"
    path = os.path.join(OUTPUT_DIR, filename)
    with open(path, "wb") as f:
        f.write(content)
    return filename, hash_md5

def process_domain(domain):
    base_url = f"https://{domain}"
    #launch playwright browser session headless mode no GUI
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True) #open source core of chrome
        # create a new browser context with a custom user-agent
        context = browser.new_context(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64)")
        page = context.new_page()
        try:
            page.goto(base_url, timeout=15000) #15secs in case of slow sites 
            time.sleep(2)   # wait 2 seconds to allow any js rendered content to load
            content = page.content() # extract the HTML content after all JS is done
            soup = BeautifulSoup(content, "html.parser")  # parse the HTML with Bs for easier element searching
            logo = extract_logo(soup, base_url)

            if logo is None:
                raise ValueError("No logo found")
            # 1 inline svg logo 
            if isinstance(logo, tuple) and logo[0] == "inline_svg":
                svg_content = logo[1].encode('utf-8') #convert svg to bytes  for deduplication
                filename, img_hash = save_logo(svg_content, domain, "svg")
                strategy = "inline-svg"
                #2 normal image or favicon
            else:
                response = page.request.get(logo)
                if response.ok:
                    img_content = response.body()
                    # extract file extension from URL fallback to png if unknown
                    ext = logo.split("?")[0].split(".")[-1][:4] or "png"
                    filename, img_hash = save_logo(img_content, domain, ext)
                    strategy = "img-or-favicon"
                else:
                    raise ValueError("Image fetch failed")

            browser.close()
            return domain, "success", strategy, filename, img_hash, ""  # on success, return details domain, status, strategy used, filename, hash, no error
        except Exception as e:
            browser.close()
            return domain, "fail", "", "", "", str(e)

def main():
    results = []
    with open(INPUT_CSV, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        domains = [row["domain"] for row in reader]

    for domain in domains:
        print(f"Processing {domain}...")
        res = process_domain(domain)
        print(res)
        results.append(res)

    with open(RESULTS_CSV, "w", encoding="utf-8", newline='') as f:
        writer = csv.writer(f)
        writer.writerow(["domain", "status", "strategy", "filename", "hash", "error"])
        writer.writerows(results)

    success_count = sum(1 for r in results if r[1] == "success")
    print(f"\nFinal results: {success_count}/{len(results)} logos extracted successfully.")

if __name__ == "__main__":
    main()


    # Secondary script to reprocess failed domains
# Attempts logo extraction again for sites that didn’t work in the first round 