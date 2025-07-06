import requests
import csv
import time

FAILED_CSV = "data/failed_sites.csv"
OUT_CSV    = "data/failed_diagnostics.csv"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko)",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://google.com/"
}

def classify_browser_access(reason):
    if reason in {"blocked-bot-waf", "redirect", "server-default-page"}:
        return "yes"
    if reason in {"dns", "ssl", "timeout", "connection-error"}:
        return "no"
    if reason in {"not-found"}:
        return "yes"
    if reason in {"unexpected-html", "other-http", "unknown"}:
        return "maybe"
    return "maybe"

def diagnose_error(domain):
    url = "https://" + domain
    try:
        resp = requests.get(url, headers=HEADERS, timeout=8, verify=True, allow_redirects=True)
        txt = resp.text.lower()
        if resp.status_code == 403:
            if "cloudflare" in txt:
                return "blocked-bot-waf", "Cloudflare 403"
            if "incapsula" in txt:
                return "blocked-bot-waf", "Incapsula 403"
            return "blocked-bot-waf", "HTTP 403 Forbidden"
        if "robots" in txt and "noindex" in txt:
            return "blocked-bot-waf", "robots noindex found"
        if "apache http server test page" in txt or "testing123" in txt:
            return "server-default-page", "Default/test page served"
        if "certificate expired" in txt or "certificate verify failed" in txt:
            return "ssl", "SSL cert expired/failed"
        if resp.status_code == 200 and len(resp.text) < 500:
            if "window.location" in txt or "redirect" in txt:
                return "redirect", "HTML redirect/script"
            return "unexpected-html", f"200 OK but suspiciously short ({len(resp.text)} bytes)"
        if resp.status_code == 404:
            return "not-found", "HTTP 404"
        return "other-http", f"HTTP {resp.status_code}"
    except requests.exceptions.SSLError as ssl_e:
        return "ssl", str(ssl_e)
    except requests.exceptions.ConnectTimeout as ce:
        return "timeout", str(ce)
    except requests.exceptions.ConnectionError as ce:
        msg = str(ce)
        if "Name or service not known" in msg or "getaddrinfo failed" in msg or "NXDOMAIN" in msg:
            return "dns", msg
        return "connection-error", msg
    except Exception as e:
        msg = str(e)
        if "timed out" in msg:
            return "timeout", msg
        return "unknown", msg

def test_sites_from_failed_csv():
    seen = set()
    results = []
    with open(FAILED_CSV, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            domain = row['domain']
            if domain in seen:
                continue
            seen.add(domain)
            print(f"\nTesting: {domain}")
            reason, details = diagnose_error(domain)
            browser_accessible = classify_browser_access(reason)
            print(f"  Reason: {reason}\n  Details: {details[:180]}...\n  Browser Accessible: {browser_accessible}")
            results.append({
                "domain": domain,
                "reason": reason,
                "details": details,
                "browser_accessible": browser_accessible
            })
            time.sleep(1)

   
    with open(OUT_CSV, "w", newline="", encoding="utf-8") as cf:
        writer = csv.DictWriter(cf, fieldnames=["domain", "reason", "details", "browser_accessible"])
        writer.writeheader()
        for row in results:
            writer.writerow(row)
    
    
    total = len(results)
    n_browser_yes = sum(r['browser_accessible'] == 'yes' for r in results)
    n_browser_maybe = sum(r['browser_accessible'] == 'maybe' for r in results)
    n_browser_no = sum(r['browser_accessible'] == 'no' for r in results)
    print(f"\n[INFO] Diagnostic results saved to {OUT_CSV}")
    print(f"Total domenii eșuate: {total}")
    print(f"Accesibile din browser: {n_browser_yes}")
    print(f"Probabil accesibile (maybe): {n_browser_maybe}")
    print(f"Nu sunt accesibile: {n_browser_no}")

if __name__ == "__main__":
    test_sites_from_failed_csv()


# Script for diagnostics and debugging:
#Helps understand why logo extraction failed for certain sites. It logs the reason for each domain so you can analyze and fix issues more effectively.
