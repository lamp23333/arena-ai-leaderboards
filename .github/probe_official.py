import json
import os
import re
import sys
import urllib.error
import urllib.request

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
      "Accept-Language": "en-US,en;q=0.9"}


def fetch(u, extra=None, t=45):
    h = dict(UA)
    if extra:
        h.update(extra)
    req = urllib.request.Request(u, headers=h)
    try:
        with urllib.request.urlopen(req, timeout=t) as r:
            return r.status, r.read(), dict(r.headers)
    except urllib.error.HTTPError as e:
        return e.code, e.read(), dict(e.headers or {})
    except Exception as e:
        return "ERR", str(e).encode(), {}


print("### new v2 api without key ###")
endpoints = [
    "https://artificialanalysis.ai/api/v2/language/models",
    "https://artificialanalysis.ai/api/v2/language/models?include=all",
    "https://artificialanalysis.ai/api/v2/language/models/free",
]
for u in endpoints:
    st, body, hd = fetch(u)
    print("  EP", st, len(body), u.split("ai", 1)[-1])
    print("     body:", body[:220].decode("utf-8", "replace").replace("\n", " "))

print("### aa sitemap ###")
st, body, hd = fetch("https://artificialanalysis.ai/sitemap.xml")
print("  sitemap", st, len(body))
if st == 200:
    locs = re.findall(r"<loc>([^<]+)</loc>", body.decode("utf-8", "replace"))
    print("  LOCS", len(locs))
    models = [l for l in locs if "/models/" in l]
    print("  MODEL_PAGES", len(models))
    for l in models[:6]:
        print("    M", l)

print("### robots ###")
st, body, hd = fetch("https://artificialanalysis.ai/robots.txt")
if st == 200:
    txt = body.decode("utf-8", "replace")
    for line in txt.splitlines():
        if "sitemap" in line.lower() or "api" in line.lower():
            print("  R", line.strip())

sys.stdout.flush()
os._exit(0)
