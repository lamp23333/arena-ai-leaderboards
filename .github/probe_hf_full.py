import io
import json
import os
import sys
import urllib.request

import pyarrow as pa
import pyarrow.parquet as pq

pa.set_cpu_count(1)
pa.set_io_thread_count(1)

DS = "lmarena-ai/leaderboard-dataset"
H = "https://huggingface.co/"

def get(u, t=180):
    req = urllib.request.Request(u, headers={"User-Agent": "probe"})
    return urllib.request.urlopen(req, timeout=t).read()

# 1) full 分支里 text 有哪些文件
try:
    tree = json.loads(get(H + "api/datasets/" + DS + "/tree/refs%2Fconvert%2Fparquet/text/full"))
    print("FULL_TREE", [(x["path"], x.get("size")) for x in tree][:12])
except Exception as e:
    print("FULL_TREE_ERR", type(e).__name__, str(e)[:150])

# 2) 下载 full 的第一个文件，看它包含多少期 / 是否含 20261017
try:
    raw = get(H + "datasets/" + DS + "/resolve/refs%2Fconvert%2Fparquet/text/full/0000.parquet")
    tb = pq.read_table(io.BytesIO(raw))
    print("FULL_PARQUET bytes", len(raw), "rows", tb.num_rows, "cols", len(tb.schema.names))
    if "leaderboard_publish_date" in tb.schema.names:
        dates = [str(v) for v in tb.column("leaderboard_publish_date").to_pylist() if v]
        uniq = sorted(set(dates))
        print("FULL_DATES", len(uniq), uniq[-6:])
        if "model_name" in tb.schema.names:
            names = [str(v) for v in tb.column("model_name").to_pylist() if v]
            hits = sorted({n for n in names if "20261017" in n})
            print("FULL_1017_MODELS", hits)
            ds = [n for n in names if "deepseek" in n.lower()]
            print("FULL_DEEPSEEK_SAMPLE", sorted(set(ds))[-8:])
except Exception as e:
    print("FULL_PARQUET_ERR", type(e).__name__, str(e)[:200])

# 3) dataset card 里的更新频率说明
try:
    card = get(H + "datasets/" + DS + "/resolve/main/README.md").decode("utf-8", "replace")
    print("CARD_BYTES", len(card))
    for line in card.splitlines():
        low = line.lower()
        if any(k in low for k in ("update", "daily", "weekly", "hourly", "refresh", "schedule", "cadence")):
            print("  C", line.strip()[:170])
except Exception as e:
    print("CARD_ERR", type(e).__name__, str(e)[:150])

sys.stdout.flush()
os._exit(0)
