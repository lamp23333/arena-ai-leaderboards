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
            return r.status, r.read()
    except urllib.error.HTTPError as e:
        return e.code, e.read()
    except Exception as e:
        return "ERR", str(e).encode()


print("### migrate doc ###")
for u in ["https://artificialanalysis.ai/data-api/migrate-v2-data", "https://artificialanalysis.ai/data-api"]:
    st, body = fetch(u)
    txt = body.decode("utf-8", "replace") if isinstance(body, bytes) else str(body)
    print("  DOC", st, len(txt), u)
    plain = re.sub(r"<script[^>]*>.*?</script>", " ", txt, flags=re.S)
    plain = re.sub(r"<[^>]+>", " ", plain)
    plain = re.sub(r"\s+", " ", plain)
    for kw in ["api", "key", "token", "endpoint", "Authorization", "x-api"]:
        for mm in re.finditer(kw, plain, re.I):
            seg = plain[max(0, mm.start() - 90):mm.start() + 130]
            print("    CTX", kw, "|", seg.strip()[:220])
            break

print("### candidate endpoints ###")
for u in ["https://artificialanalysis.ai/api/v2/llms/models",
          "https://artificialanalysis.ai/api/data/llms/models",
          "https://artificialanalysis.ai/data-api/llms/models",
          "https://artificialanalysis.ai/api/v2/data/llms/models/latest"]:
    st, body = fetch(u)
    print("  CAND", st, len(body), u.split("ai/", 1)[-1], str(body[:110]))

print("### homepage embedded data ###")
st, body = fetch("https://artificialanalysis.ai/")
txt = body.decode("utf-8", "replace")
print("  page", st, len(txt))
idxs = [m.start() for m in re.finditer("intelligenceIndex", txt)]
print("  hits", len(idxs))
for i in idxs[:3]:
    print("  SNIP", txt[max(0, i - 160):i + 200].replace("\\\"", "\"")[:360])
names = re.findall(r'\\?"name\\?":\\?"([A-Z][^"\\]{1,40})\\?"', txt)
print("  NAME_CANDIDATES", len(names), names[:12])
slug = re.findall(r'/models/([a-z0-9\-]{3,40})', txt)
print("  MODEL_SLUGS", len(set(slug)), sorted(set(slug))[:15])

sys.stdout.flush()
os._exit(0)
