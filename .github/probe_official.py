import json
import os
import re
import sys
import urllib.error
import urllib.request

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
      "Accept-Language": "en-US,en;q=0.9"}


def fetch(u, extra=None, t=40):
    h = dict(UA)
    if extra:
        h.update(extra)
    req = urllib.request.Request(u, headers=h)
    try:
        with urllib.request.urlopen(req, timeout=t) as r:
            return r.status, r.read()
    except urllib.error.HTTPError as e:
        return e.code, e.read()
    except Exception as e:
        return "ERR", str(e).encode()


print("### AA endpoints ###")
for u, extra in [
    ("https://artificialanalysis.ai/api/v2/data/llms/models", None),
    ("https://artificialanalysis.ai/api/v2/data/llms/models", {"x-api-key": "demo"}),
    ("https://artificialanalysis.ai/api/v2/data/llms/creators", None),
]:
    st, body = fetch(u, extra)
    tag = "NOAUTH" if not extra else ("APIKEY=" + extra.get("x-api-key", ""))
    print("  AA", tag, st, len(body), u.split("ai/", 1)[-1])
    print("     head:", body[:200].decode("utf-8", "replace").replace("\n", " "))

print("### AA homepage scan ###")
st, body = fetch("https://artificialanalysis.ai/")
print("  page", st, len(body))
txt = body.decode("utf-8", "replace")
for probe in ["__next_f", "intelligenceIndex", "intelligence_index", "x-api-key", "api/v2", "median_output_tokens", "self.__next_f"]:
    print("  COUNT", probe, txt.count(probe))
paths = sorted(set(re.findall(r'"(/api/[a-zA-Z0-9_\-/]*)"', txt)))[:20]
print("  api paths:", paths)
print("### arena sitemap locs ###")
st, body = fetch("https://arena.ai/sitemap.xml")
print("  sitemap", st, len(body))
locs = re.findall(r"<loc>([^<]+)</loc>", body.decode("utf-8", "replace"))
print("  LOCS", len(locs))
for l in locs:
    print("   S", l.replace("https://arena.ai", ""))

sys.stdout.flush()
os._exit(0)
