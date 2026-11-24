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


st, body = fetch("https://artificialanalysis.ai/")
txt = body.decode("utf-8", "replace")
print("page", st, len(txt))

# RSC payload chunks: self.__next_f.push([1,"..."]) -> unescape to recover embedded JSON
chunks = re.findall(r'self\.__next_f\.push\(\[1,"(.*?)"\]\)', txt, re.S)
print("RSC_CHUNKS", len(chunks))
blob = ""
for c in chunks:
    try:
        blob += json.loads('"' + c + '"')
    except Exception:
        pass
print("BLOB_LEN", len(blob))

# find model objects: they carry slug + name + intelligenceIndex
objs = re.findall(r'\{"slug":"([a-z0-9\-]{2,50})","name":"([^"]{1,60})"([^{}]{0,4000}?)"intelligenceIndex":([0-9.]+)', blob)
print("MODEL_OBJS", len(objs))
for slug, name, mid, ii in objs[:5]:
    extra = ""
    for k in ("isOpenWeights", "parameters", "score", "omniscienceAccuracy"):
        m = re.search(r'"' + k + r'":([^,\}]*)', mid)
        if m:
            extra += f" {k}={m.group(1)}"
    print(f"  {slug:34s} {name[:26]:26s} II={float(ii):.1f}{extra}")

# also count any 'slug' occurrences to see coverage
all_slugs = set(re.findall(r'"slug":"([a-z0-9\-]{2,50})"', blob))
print("DISTINCT_SLUGS", len(all_slugs))
field_pool = set()
for m in re.finditer(r'"([a-zA-Z][a-zA-Z0-9]{2,30})":', blob):
    field_pool.add(m.group(1))
key_fields = [f for f in field_pool if any(k in f.lower() for k in ("intelligence", "score", "index", "elo", "accuracy", "tokens", "price", "released"))]
print("FIELDS_SAMPLE", sorted(key_fields)[:28])

sys.stdout.flush()
os._exit(0)
