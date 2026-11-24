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


def slugs_with_index(blob):
    out = {}
    for m in re.finditer(r'"intelligenceIndex":([0-9.eE\-]+)', blob):
        back = blob[max(0, m.start() - 3000):m.start()]
        last = list(re.finditer(r'"slug":"([a-z0-9\-\.]{2,50})"', back))
        if last:
            out[last[-1].group(1)] = m.group(1)
    return out


for path in ["/models/releases", "/models/comparisons", "/models/glm-4-5v", "/models/multilingual"]:
    st, body = fetch("https://artificialanalysis.ai" + path)
    if st != 200:
        print("PATH", path, st, len(body))
        continue
    html = body.decode("utf-8", "replace")
    blob = payload(html)
    d = slugs_with_index(blob)
    print("PATH", path, st, "html", len(html), "blob", len(blob), "models", len(d))
    if d:
        items = sorted(d.items(), key=lambda kv: -float(kv[1]))
        print("   top:", [(k, round(float(v), 1)) for k, v in items[:5]])

sys.stdout.flush()
os._exit(0)
