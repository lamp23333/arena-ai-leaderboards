import json
import os
import sys
import urllib.error
import urllib.request

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"}


def get(u, t=40):
    req = urllib.request.Request(u, headers=UA)
    with urllib.request.urlopen(req, timeout=t) as r:
        return r.read()


print("### HF org info ###")
try:
    org = json.loads(get("https://huggingface.co/api/organizations/lmarena-ai"))
    for k in ["name", "fullname", "isVerified", "isOrg", "isUser", "numUsers", "numModels", "numDatasets", "createdAt"]:
        if k in org:
            print("  ORG", k, "=", org[k])
except Exception as e:
    print("  ORG_ERR", type(e).__name__, str(e)[:120])

print("### dataset meta ###")
try:
    ds = json.loads(get("https://huggingface.co/api/datasets/lmarena-ai/leaderboard-dataset"))
    for k in ["id", "author", "gated", "private", "downloads", "likes", "lastModified", "createdAt"]:
        if k in ds:
            print("  DS", k, "=", ds[k])
    cd = ds.get("cardData") or {}
    print("  CARD_KEYS", list(cd.keys())[:12])
    for k in ("license", "source", "pretty_name", "organization"):
        if k in cd:
            print("  CARD", k, "=", cd[k])
except Exception as e:
    print("  DS_ERR", type(e).__name__, str(e)[:120])

print("### card text: lines mentioning official / arena ###")
try:
    card = get("https://huggingface.co/datasets/lmarena-ai/leaderboard-dataset/resolve/main/README.md").decode("utf-8", "replace")
    for line in card.splitlines():
        low = line.lower()
        if any(k in low for k in ("official", "arena.ai", "lmarena", "maintained", "source of truth", "api")):
            print("  T", line.strip()[:180])
except Exception as e:
    print("  CARD_ERR", type(e).__name__, str(e)[:120])

print("### leaderboard sites reachability ###")
SITES = [
    "https://lmarena.ai/leaderboard",
    "https://artificialanalysis.ai/",
    "https://livebench.ai/",
    "https://www.swebench.com/",
    "https://crfm.stanford.edu/helm/",
    "https://rank.opencompass.org.cn/",
    "https://www.superclueai.com/",
    "https://scale.com/leaderboard",
    "https://www.datalearner.com/leaderboards",
    "https://vals.ai/",
    "https://epoch.ai/benchmarks",
    "https://designarena.ai/",
]
for u in SITES:
    try:
        req = urllib.request.Request(u, headers=UA)
        with urllib.request.urlopen(req, timeout=25) as r:
            body = r.read()
            print("  SITE", r.status, len(body), u)
    except urllib.error.HTTPError as e:
        print("  SITE", e.code, 0, u)
    except Exception as e:
        print("  SITE", "ERR", type(e).__name__, u)

sys.stdout.flush()
os._exit(0)
