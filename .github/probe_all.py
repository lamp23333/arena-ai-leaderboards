import io, json, urllib.request
import pyarrow as pa
import pyarrow.parquet as pq

pa.set_cpu_count(1)
pa.set_io_thread_count(1)

DS = "lmarena-ai/leaderboard-dataset"
BASE = f"https://huggingface.co/datasets/{DS}/resolve/refs%2Fconvert%2Fparquet"
CONFIGS = ["agent", "agent_bash_recovery_steps", "agent_bash_reliability", "agent_capability",
           "agent_praise_complaint", "agent_steerability", "agent_task_outcome",
           "agent_task_outcome_explicit", "agent_tool_efficiency", "agent_tool_hallucination",
           "document", "document_style_control", "image_edit", "image_to_video", "search",
           "search_factuality", "search_style_control", "text", "text_factuality",
           "text_style_control", "text_to_image", "text_to_video", "video_edit", "vision",
           "vision_style_control", "webdev"]

def get(u, timeout=150):
    r = urllib.request.Request(u, headers={"User-Agent": "probe"})
    return urllib.request.urlopen(r, timeout=timeout).read()

for cfg in CONFIGS:
    u = f"{BASE}/{cfg}/latest/0000.parquet"
    try:
        raw = get(u)
        tb = pq.read_table(io.BytesIO(raw))
        names = tb.schema.names
        cats = sorted({str(x) for x in tb.column("category").to_pylist() if x}) if "category" in names else []
        dcol = "leaderboard_publish_date" if "leaderboard_publish_date" in names else None
        dates = sorted({str(x) for x in tb.column(dcol).to_pylist() if x}) if dcol else []
        score_col = "rating" if "rating" in names else ("score" if "score" in names else "?")
        print(f"CFG {cfg:32s} bytes={len(raw):8d} rows={tb.num_rows:6d} score={score_col:8s} date={dates[-1] if dates else '-'} cats({len(cats)})={cats[:10]}")
    except Exception as e:
        print(f"CFG {cfg:32s} ERR {type(e).__name__}: {str(e)[:120]}")
