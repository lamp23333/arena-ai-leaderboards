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
chunks = re.findall(r'self\.__next_f\.push\(\[1,"(.*?)"\]\)', txt, re.S)
blob = ""
for c in chunks:
    try:
        blob += json.loads('"' + c + '"')
    except Exception:
        pass

print("BLOB_LEN", len(blob))

pairs = []
for m in re.finditer(r'"intelligenceIndex":([0-9.eE\-]+)', blob):
    pos = m.start()
    back = blob[max(0, pos - 2500):pos]
    sm = None
    last = list(re.finditer(r'"slug":"([a-z0-9\-\.]{2,50})"', back))
    if last:
        sm = last[-1].group(1)
    nm = list(re.finditer(r'"name":"([^"]{1,70})"', back))
    nmv = nm[-1].group(1) if nm else None
    if sm:
        pairs.append((sm, nmv, m.group(1)))

print("PAIRS", len(pairs))
seen = set()
uniq = []
for s, n, v in pairs:
    if s in seen:
        continue
    seen.add(s)
    uniq.append((s, n, v))
print("UNIQUE", len(uniq))
for s, n, v in uniq[:12]:
    print(f"  {s:32s} {str(n)[:26]:26s} II={v}")

# dump one full object by brace balancing from the '{' nearest before the slug
if uniq:
    target = uniq[0][0]
    idx = blob.find('"slug":"' + target + '"')
    start = blob.rfind("{", 0, idx)
    depth = 0
    end = start
    for i in range(start, min(len(blob), start + 12000)):
        ch = blob[i]
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                end = i + 1
                break
    obj = blob[start:end]
    print("OBJ_LEN", len(obj))
    print("OBJ_HEAD", obj[:1200])

print("### sitemap leaderboard paths ###")
st, sb = fetch("https://arena.ai/sitemap.xml")
locs = re.findall(r"<loc>([^<]+)</loc>", sb.decode("utf-8", "replace"))
lbs = [l.replace("https://arena.ai", "") for l in locs if "/leaderboard" in l]
print("LB", len(lbs))
for l in lbs:
    print("  P", l)

sys.stdout.flush()
os._exit(0)
