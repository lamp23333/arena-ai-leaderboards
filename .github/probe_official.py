import json
import os
import re
import sys
import urllib.request

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"}

req = urllib.request.Request("https://artificialanalysis.ai/models/comparisons", headers=UA)
with urllib.request.urlopen(req, timeout=60) as r:
    html = r.read().decode("utf-8", "replace")

chunks = re.findall(r'self\.__next_f\.push\(\[1,"(.*?)"\]\)', html, re.S)
blob = ""
for c in chunks:
    try:
        blob += json.loads('"' + c + '"')
    except Exception:
        pass
print("BLOB", len(blob))

dec = json.JSONDecoder()
found = []
for m in re.finditer(r'"[A-Za-z_]{2,24}"\s*:\s*\[', blob):
    start = blob.find("[", m.start())
    try:
        arr, _ = dec.raw_decode(blob, start)
    except Exception:
        continue
    if not isinstance(arr, list) or len(arr) < 3:
        continue
    hits = [x for x in arr if isinstance(x, dict) and ("intelligenceIndex" in x or "intelligence_index" in x)]
    if hits:
        found = hits
        print("ARRAY_KEY", m.group(0)[:40], "len", len(arr), "models", len(hits))
        break

if found:
    obj = found[0]
    print("TOP_KEYS", sorted(obj.keys()))
    print("FULL_JSON", json.dumps(obj, ensure_ascii=False)[:2600])

    price_keys = []
    stack = [(obj, "")]
    while stack:
        cur, path = stack.pop()
        if isinstance(cur, dict):
            for k, v in cur.items():
                p = path + "." + k if path else k
                if isinstance(v, (dict, list)):
                    stack.append((v, p))
                elif isinstance(v, (int, float)) and any(t in k.lower() for t in ("price", "cost", "token", "speed", "per_second")):
                    price_keys.append((p, v))
    print("NUMERIC_LEAVES")
    for p, v in price_keys[:30]:
        print("  ", p, "=", v)

sys.stdout.flush()
os._exit(0)
