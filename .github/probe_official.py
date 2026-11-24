import json
import os
import re
import sys
import urllib.error
import urllib.request

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
      "Accept-Language": "en-US,en;q=0.9"}


def fetch(u, t=60):
    req = urllib.request.Request(u, headers=dict(UA))
    try:
        with urllib.request.urlopen(req, timeout=t) as r:
            return r.status, r.read()
    except urllib.error.HTTPError as e:
        return e.code, e.read()
    except Exception as e:
        return "ERR", str(e).encode()


def payload(html):
    chunks = re.findall(r'self\.__next_f\.push\(\[1,"(.*?)"\]\)', html, re.S)
    blob = ""
    for c in chunks:
        try:
            blob += json.loads('"' + c + '"')
        except Exception:
            pass
    return blob


def count_models(blob):
    slugs = set()
    for m in re.finditer(r'"intelligenceIndex":([0-9.eE\-]+)', blob):
        back = blob[max(0, m.start() - 3000):m.start()]
        last = list(re.finditer(r'"slug":"([a-z0-9\-\.]{2,50})"', back))
        if last:
            slugs.add(last[-1].group(1))
    return slugs


for path in ["/models", "/leaderboards", "/leaderboard", "/models/language", "/compare"]:
    st, body = fetch("https://artificialanalysis.ai" + path)
    if st != 200:
        print("PATH", path, st, len(body))
        continue
    html = body.decode("utf-8", "replace")
    blob = payload(html)
    slugs = count_models(blob)
    print("PATH", path, st, "html", len(html), "blob", len(blob), "models", len(slugs))
    if slugs:
        print("   sample", sorted(slugs)[:8])

print("### sitemap video + agent paths ###")
st, sb = fetch("https://arena.ai/sitemap.xml")
locs = re.findall(r"<loc>([^<]+)</loc>", sb.decode("utf-8", "replace"))
for l in locs:
    p = l.replace("https://arena.ai", "")
    if "/video" in p or "/agent" in p or "/leaderboard" == p:
        print("  P", p)

sys.stdout.flush()
os._exit(0)
