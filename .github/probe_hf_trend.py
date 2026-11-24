import io
import os
import sys
import urllib.request

import pyarrow as pa
import pyarrow.parquet as pq

pa.set_cpu_count(1)
pa.set_io_thread_count(1)

URL = "https://huggingface.co/datasets/lmarena-ai/leaderboard-dataset/resolve/refs%2Fconvert%2Fparquet/text/full/0000.parquet"
KEYS = ["gemini-4-carbon", "gemini-4-argon", "gemini-4-neon",
        "claude-fable-5-2", "claude-opus-5-5", "claude-fable-5-high"]

raw = urllib.request.urlopen(urllib.request.Request(URL, headers={"User-Agent": "probe"}), timeout=300).read()
tb = pq.read_table(io.BytesIO(raw))
print("TOTAL_ROWS", tb.num_rows)

rows = tb.to_pylist()
series = {}
for r in rows:
    if r.get("category") != "overall":
        continue
    n = str(r.get("model_name") or "")
    for k in KEYS:
        if n == k or n.startswith(k + "-") or n == k:
            series.setdefault(n, []).append(
                (str(r.get("leaderboard_publish_date")), round(r.get("rating") or 0, 1), r.get("vote_count"), r.get("rank")))

for name in sorted(series):
    s = sorted(series[name], key=lambda x: x[0])
    print("SERIES", name, "points=", len(s), "first=", s[0], "last=", s[-1])
    for p in s[-6:]:
        print("   P", name, p[0], p[1], "votes=", p[2], "rank=", p[3])

sys.stdout.flush()
os._exit(0)
