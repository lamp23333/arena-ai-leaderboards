import io
import json
import os
import sys
import urllib.request

import pyarrow as pa
import pyarrow.parquet as pq

pa.set_cpu_count(1)
pa.set_io_thread_count(1)

HF = "https://huggingface.co/datasets/lmarena-ai/leaderboard-dataset/resolve/refs%2Fconvert%2Fparquet/text/latest/0000.parquet"
MINE = "https://raw.githubusercontent.com/lamp23333/arena-ai-leaderboards/main/data/2026-11-24/text.json"

raw = urllib.request.urlopen(urllib.request.Request(HF, headers={"User-Agent": "v"}), timeout=200).read()
tb = pq.read_table(io.BytesIO(raw))
rows = [r for r in tb.to_pylist() if r.get("category") == "overall"]
print("HF_OVERALL_ROWS", len(rows))

mine = json.loads(urllib.request.urlopen(urllib.request.Request(MINE, headers={"User-Agent": "v"}), timeout=60).read())
mine_models = mine["models"]
print("MINE_ROWS", len(mine_models))

hf = {}
for r in rows:
    hf[str(r.get("model_name"))] = r

mismatch_rank = 0
mismatch_score = 0
mismatch_votes = 0
mismatch_ci = 0
samples = []
for m in mine_models:
    name = m.get("model_display")
    r = hf.get(name)
    if r is None:
        continue
    hf_rank = r.get("rank")
    if hf_rank is not None and int(hf_rank) != int(m["rank"]):
        mismatch_rank += 1
        if len(samples) < 8:
            samples.append((name, "hf_rank", hf_rank, "my_rank", m["rank"], "score", round(r.get("rating") or 0, 2)))
    if abs(float(r.get("rating") or 0) - float(m["score"])) > 1e-6:
        mismatch_score += 1
    if r.get("vote_count") is not None and int(r.get("vote_count")) != int(m["votes"] or -1):
        mismatch_votes += 1
    lo, hi = r.get("rating_lower"), r.get("rating_upper")
    if lo is not None and hi is not None:
        ci = round((hi - lo) / 2.0, 4)
        if abs(ci - float(m["ci"] or 0)) > 1e-3:
            mismatch_ci += 1

print("RANK_MISMATCH", mismatch_rank)
print("SCORE_MISMATCH", mismatch_score)
print("VOTES_MISMATCH", mismatch_votes)
print("CI_MISMATCH", mismatch_ci)
for s in samples:
    print("  DIFF", s)

# 反向：HF 有而我没有的
mine_names = {m.get("model_display") for m in mine_models}
missing = [n for n in hf if n not in mine_names]
print("IN_HF_NOT_IN_MINE", len(missing), missing[:5])
print("HF_SAMPLE_ROW", json.dumps(rows[0], ensure_ascii=False)[:400])

sys.stdout.flush()
os._exit(0)
