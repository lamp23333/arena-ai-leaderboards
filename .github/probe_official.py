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

# what arrays exist and how complete are their objects
for m in re.finditer(r'"([A-Za-z_]{2,30})"\s*:\s*\[\s*\{', blob):
    key = m.group(1)
    start = blob.find("[", m.start())
    try:
        arr, _ = dec.raw_decode(blob, start)
    except Exception:
        continue
    if not isinstance(arr, list) or len(arr) < 2:
        continue
    models = [x for x in arr if isinstance(x, dict) and "slug" in x and "intelligenceIndex" in x]
    if not models:
        continue
    with_price = sum(1 for x in models if x.get("price1mOutputTokens") is not None)
    print(f"ARR {key:24s} len={len(arr):4d} models={len(models):3d} with_price={with_price:3d}")

# inspect every object whose slug is claude-fable-5-2
target = "claude-fable-5-2"
count = 0
for m in re.finditer(r'"slug"\s*:\s*"' + re.escape(target) + r'"', blob):
    start = blob.rfind("{", max(0, m.start() - 200), m.start())
    tries = 0
    while start >= 0 and tries < 4:
        tries += 1
        try:
            obj, _ = dec.raw_decode(blob, start)
        except Exception:
            start = blob.rfind("{", 0, start)
            continue
        if isinstance(obj, dict) and obj.get("slug") == target:
            count += 1
            print("OBJ", count, "keys", len(obj),
                  "| name", obj.get("name"),
                  "| II", round(obj.get("intelligenceIndex") or 0, 2),
                  "| in", obj.get("price1mInputTokens"),
                  "| out", obj.get("price1mOutputTokens"),
                  "| effort", (obj.get("effort") or {}).get("label") if isinstance(obj.get("effort"), dict) else obj.get("effort"))
        break
print("TARGET_OBJECTS", count)

sys.stdout.flush()
os._exit(0)
