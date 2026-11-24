import json, io, urllib.request

DS = "lmarena-ai/leaderboard-dataset"

def get(u, timeout=120):
    r = urllib.request.Request(u, headers={"User-Agent": "probe"})
    return urllib.request.urlopen(r, timeout=timeout).read()

try:
    sp = json.loads(get(f"https://datasets-server.huggingface.co/splits?dataset={DS}"))
    cfgs = sorted({s["config"] for s in sp.get("splits", [])})
    print("CONFIGS:", cfgs)
except Exception as e:
    print("SPLITS_ERR:", type(e).__name__, str(e)[:200])

try:
    t = json.loads(get(f"https://huggingface.co/api/datasets/{DS}/tree/refs%2Fconvert%2Fparquet?recursive=1"))
    print("CONVERT_TREE:", [(x["path"], x.get("size")) for x in t][:40])
except Exception as e:
    print("TREE_ERR:", type(e).__name__, str(e)[:200])

import pyarrow.parquet as pq
for cfg in ["text", "agent"]:
    u = f"https://huggingface.co/datasets/{DS}/resolve/refs%2Fconvert%2Fparquet/{cfg}/latest/0000.parquet"
    try:
        raw = get(u)
        tb = pq.read_table(io.BytesIO(raw))
        print(f"[{cfg}] bytes={len(raw)} rows={tb.num_rows}")
        print(f"[{cfg}] SCHEMA={tb.schema.names}")
        print(f"[{cfg}] SAMPLE=", json.dumps(tb.slice(0, 2).to_pylist(), ensure_ascii=False)[:900])
        if "leaderboard_publish_date" in tb.schema.names:
            vals = [str(v) for v in tb.column("leaderboard_publish_date").to_pylist() if v]
            print(f"[{cfg}] PUBLISH_DATES: n={len(set(vals))} latest={max(vals) if vals else None}")
    except Exception as e:
        print(f"[{cfg}] ERR:", type(e).__name__, str(e)[:300])
