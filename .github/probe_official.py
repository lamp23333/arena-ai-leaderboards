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


def rsc_blob(html):
    chunks = re.findall(r'self\.__next_f\.push\(\[1,"(.*?)"\]\)', html, re.S)
    out = []
    for c in chunks:
        try:
            out.append(json.loads('"' + c + '"'))
        except Exception:
            pass
    return "".join(out)


dec = json.JSONDecoder()

for path in ["/leaderboards/models", "/leaderboards/providers"]:
    st, body = fetch("https://artificialanalysis.ai" + path)
    html = body.decode("utf-8", "replace")
    blob = rsc_blob(html)
    print(f"PAGE {path} status={st} html={len(html)} blob={len(blob)}")
    for prop in ("initialModels", "initialRows", "releases", "hosts", "capabilityIndexes"):
        m = re.search(r'"' + prop + r'"\\s*:\\s*\\[', blob)
        if not m:
            continue
        start = blob.find("[", m.start())
        try:
            arr, _ = dec.raw_decode(blob, start)
        except Exception as exc:
            print("   PROP", prop, "decode failed", type(exc).__name__)
            continue
        if not isinstance(arr, list):
            continue
        sample = arr[0] if arr and isinstance(arr[0], dict) else {}
        priced = sum(1 for x in arr if isinstance(x, dict) and x.get("price1mOutputTokens") is not None)
        indexed = sum(1 for x in arr if isinstance(x, dict) and "intelligenceIndex" in x)
        print(f"   PROP {prop:20s} len={len(arr):4d} priced={priced:4d} indexed={indexed:4d} keys={len(sample)} {sorted(list(sample.keys()))[:12]}")

sys.stdout.flush()
os._exit(0)
