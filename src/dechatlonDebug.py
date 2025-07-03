import requests

headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko)"}

print("DECATHLON:")
try:
    r = requests.get("https://decathlon.com.br", headers=headers, timeout=8)
    print("Status:", r.status_code)
    print("Len HTML:", len(r.text))
except Exception as e:
    print("Eroare Decathlon:", e)

print("NESTLE:")
try:
    r = requests.get("https://nestle.do", headers=headers, timeout=8)
    print("Status:", r.status_code)
    print("Len HTML:", len(r.text))
except Exception as e:
    print("Eroare Nestle:", e)
