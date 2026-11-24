import json
import os
import re
import sys
import urllib.error
import urllib.request

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
      "Accept-Language": "en-US,en;q=0.9"}

FIXED = {"recommend", "releases", "comparisons", "multilingual", "caching", "providers"}


def fetch(u, extra=None, t=60):
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


def rsc_blob(html):
    chunks = re.findall(r'self\.__next_f\.push\(\[1,"(.*?)"\]\)', html, re.S)
    out = []
    for c in chunks:
        try:
            out.append(json.loads('"' + c + '"'))
        except Exception:
            pass
    return "".join(out)


st, body = fetch("https://artificialanalysis.ai/sitemap.xml")
locs = re.findall(r"<loc>([^<]+)</loc>", body.decode("utf-8", "replace"))
model_urls = []
for l in locs:
    m = re.match(r"https://artificialanalysis\.ai/models/([a-z0-9][a-z0-9\-\.]*)$", l)
    if not m:
        continue
    slug = m.group(1)
    if slug in FIXED:
        continue
    model_urls.append(slug)
uniq = sorted(set(model_urls))
print("SITEMAP", len(locs), "MODEL_SLUGS", len(uniq))
print("SAMPLE", uniq[:8])

# how many providers subpages exist (noise)
prov = [l for l in locs if "/providers" in l]
print("PROVIDER_SUBPAGES", len(prov))

for slug in uniq[:3]:
    u = "https://artificialanalysis.ai/models/" + slug
    st, body = fetch(u)
    html = body.decode("utf-8", "replace")
    blob = rsc_blob(html)
    has_index = "intelligenceIndex" in blob
    has_price = "price1mOutputTokens" in blob
    # is the model's own object inside?
    own = bool(re.search(r'"slug"\s*:\s*"' + re.escape(slug) + r'"', blob))
    print(f"PAGE {slug:28s} status={st} html={len(html):8d} blob={len(blob):8d} index={has_index} price={has_price} own_slug={own}")

# try RSC header on one page (cheaper payload?)
slug = uniq[0]
st, body = fetch("https://artificialanalysis.ai/models/" + slug, {"RSC": "1"})
print("RSC_HEADER", st, len(body), body[:120])

sys.stdout.flush()
os._exit(0)
