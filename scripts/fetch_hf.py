#!/usr/bin/env python3
"""Fetch LMArena leaderboards from the official HuggingFace dataset.

Source: https://huggingface.co/datasets/lmarena-ai/leaderboard-dataset
(parquet mirror served from refs/convert/parquet)

Why this exists: arena.ai sits behind Cloudflare bot management, which answers
GitHub-hosted runners with HTTP 403 / "Just a moment...". The same data is
published by LMArena as structured parquet, so no scraping, headless browser or
LLM extraction is needed - and it costs nothing to run.

Outputs per run:
  data/<date>/<slug>.json      overall board (original schema, compat)
  data/<date>/all/<slug>.json  every category slice
  data/<date>/_index.json      run summary
  data/latest.json             pointer to newest date
  BOARDS.md                    human readable top-10 digest
"""

import io
import json
import os
import re
import sys
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq
from jsonschema import Draft202012Validator

pa.set_cpu_count(1)
pa.set_io_thread_count(1)

DATASET = "lmarena-ai/leaderboard-dataset"
SOURCE_URL = "https://huggingface.co/datasets/" + DATASET
PARQUET_BASE = "https://huggingface.co/datasets/" + DATASET + "/resolve/refs%2Fconvert%2Fparquet"

CONFIGS = [
    "agent",
    "agent_bash_recovery_steps",
    "agent_bash_reliability",
    "agent_capability",
    "agent_praise_complaint",
    "agent_steerability",
    "agent_task_outcome",
    "agent_task_outcome_explicit",
    "agent_tool_efficiency",
    "agent_tool_hallucination",
    "document",
    "document_style_control",
    "image_edit",
    "image_to_video",
    "search",
    "search_factuality",
    "search_style_control",
    "text",
    "text_factuality",
    "text_style_control",
    "text_to_image",
    "text_to_video",
    "video_edit",
    "vision",
    "vision_style_control",
    "webdev",
]


def http_get(url, timeout=240, attempts=3):
    last = None
    for i in range(attempts):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "arena-leaderboard-bot/2.0"})
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return resp.read()
        except Exception as exc:
            last = exc
            print("    attempt %d failed: %s" % (i + 1, exc), file=sys.stderr)
            if i < attempts - 1:
                time.sleep(3 * (i + 1))
    raise RuntimeError("GET failed for %s: %s" % (url, last))


def pick(names, *cands):
    for c in cands:
        if c in names:
            return c
    return None


def to_float(value):
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    try:
        return float(str(value).replace(",", "").replace("%", "").strip())
    except Exception:
        return None


def to_int(value):
    f = to_float(value)
    return None if f is None else int(round(f))


def norm_license(value):
    if not isinstance(value, str):
        return None
    s = value.strip().lower()
    if not s:
        return None
    if s == "proprietary":
        return "proprietary"
    return "open"


def slugify(config):
    return config.replace("_", "-")


def detect_columns(names):
    cols = {}
    cols["model"] = pick(names, "model_name", "model", "name")
    cols["org"] = pick(names, "organization", "org", "vendor")
    cols["license"] = pick(names, "license")
    cols["category"] = pick(names, "category")
    cols["date"] = pick(names, "leaderboard_publish_date", "publish_date", "date")
    cols["rank"] = pick(names, "rank")
    cols["score"] = pick(names, "rating", "score", "elo", "value", "mean", "mean_score", "win_rate")
    cols["lower"] = pick(names, "rating_lower", "score_ci_lower", "ci_lower", "lower")
    cols["upper"] = pick(names, "rating_upper", "score_ci_upper", "ci_upper", "upper")
    cols["votes"] = pick(names, "vote_count", "observation_count", "session_count", "sessions")

    if not cols["score"]:
        blocked = {v for v in cols.values() if v}
        for key in sorted(names):
            if key in blocked:
                continue
            low = key.lower()
            if any(tag in low for tag in ("score", "rating", "elo", "value", "mean", "rate", "pct", "accuracy")):
                cols["score"] = key
                break
    return cols


def model_slug(display):
    """'Gemini 4 Carbon (High)' -> 'gemini-4-carbon-high' (matches historical naming)."""
    s = display.strip().lower().replace("&", "and")
    suffix = ""
    m = re.search(r"\(([^)]*)\)\s*$", s)
    if m:
        suffix = m.group(1).strip()
        s = s[: m.start()].strip()
    s = s.replace(".", "-").replace("/", "-")
    s = re.sub(r"[^a-z0-9]+", "-", s).strip("-")
    if suffix:
        suffix = re.sub(r"[^a-z0-9]+", "-", suffix).strip("-")
        s = (s + "-" + suffix) if s else suffix
    return s


def row_to_model(row, cols, rank):
    score = to_float(row.get(cols["score"])) if cols["score"] else None
    lo = to_float(row.get(cols["lower"])) if cols["lower"] else None
    hi = to_float(row.get(cols["upper"])) if cols["upper"] else None
    ci = round((hi - lo) / 2.0, 4) if (lo is not None and hi is not None) else None
    raw_model = row.get(cols["model"]) if cols["model"] else None
    display = str(raw_model) if raw_model is not None else ""
    return {
        "rank": rank,
        "model": model_slug(display) or display.lower() or "unknown",
        "model_display": display or None,
        "vendor": (str(row.get(cols["org"])) if cols["org"] and row.get(cols["org"]) is not None else None),
        "license": norm_license(row.get(cols["license"])) if cols["license"] else None,
        "score": score,
        "ci": ci,
        "votes": to_int(row.get(cols["votes"])) if cols["votes"] else None,
    }


def sort_key(model):
    return (-(model["score"] if model["score"] is not None else -1e18), model["model"])


def build_boards(config, rows):
    names = set(rows[0].keys())
    cols = detect_columns(names)
    if not cols["model"]:
        raise ValueError("no model column found in %s" % sorted(names))

    dates = []
    if cols["date"]:
        dates = sorted({str(r.get(cols["date"])) for r in rows if r.get(cols["date"])})
    publish_date = dates[-1] if dates else None

    # overall slice
    if cols["category"]:
        overall = [r for r in rows if str(r.get(cols["category"]) or "").strip().lower() == "overall"]
    else:
        overall = list(rows)
    note = None
    if not overall:
        overall = list(rows)
        note = "no 'overall' category, exported every row"

    def build(selection):
        items = [row_to_model(r, cols, 0) for r in selection]
        items = [m for m in items if m["model_display"]]
        items.sort(key=sort_key)
        for idx, m in enumerate(items, 1):
            m["rank"] = idx
        return items

    overall_models = build(overall)

    # every category slice
    slices = {}
    if cols["category"]:
        grouped = {}
        for r in rows:
            cat = str(r.get(cols["category"]) or "unknown").strip() or "unknown"
            grouped.setdefault(cat, []).append(r)
        for cat in sorted(grouped):
            built = build(grouped[cat])
            if built:
                slices[cat] = built
    else:
        slices["overall"] = overall_models

    return cols, publish_date, overall_models, slices, note


def render_boards_md(all_payload, fetched_at):
    lines = []
    lines.append("# LMArena leaderboards — auto-generated overview")
    lines.append("")
    lines.append("Source: [%s](%s) · fetched at `%s`" % (DATASET, SOURCE_URL, fetched_at))
    lines.append("")
    lines.append("Data files: `data/<date>/<slug>.json` (overall) and `data/<date>/all/<slug>.json` (every category).")
    lines.append("")
    for slug in sorted(all_payload):
        info = all_payload[slug]
        lines.append("## %s" % slug)
        lines.append("")
        meta = info["meta"]
        lines.append("publish date `%s` · %d rows · categories: %s" % (
            meta.get("last_updated"), meta.get("rows"), ", ".join(info["categories"][:12]) + ("…" if len(info["categories"]) > 12 else "")))
        lines.append("")
        lines.append("| # | model | vendor | score | ±ci | votes |")
        lines.append("|---|---|---|---|---|---|")
        for m in info["overall"][:10]:
            lines.append("| %s | %s | %s | %s | %s | %s |" % (
                m["rank"], m["model"], m["vendor"] or "-",
                "-" if m["score"] is None else round(m["score"], 2),
                "-" if m["ci"] is None else round(m["ci"], 2),
                "-" if m["votes"] is None else m["votes"]))
        lines.append("")
    return "\n".join(lines)


def main():
    repo_root = Path(__file__).resolve().parent.parent
    schema_dir = repo_root / "schemas"
    lb_schema = json.loads((schema_dir / "leaderboard.json").read_text())
    agent_schema = json.loads((schema_dir / "agent_leaderboard.json").read_text())
    idx_schema = json.loads((schema_dir / "index.json").read_text())
    lb_validator = Draft202012Validator(lb_schema)
    agent_validator = Draft202012Validator(agent_schema)
    idx_validator = Draft202012Validator(idx_schema)

    now = datetime.now(timezone.utc)
    date_str = now.strftime("%Y-%m-%d")
    day_dir = repo_root / "data" / date_str
    all_dir = day_dir / "all"
    day_dir.mkdir(parents=True, exist_ok=True)
    all_dir.mkdir(parents=True, exist_ok=True)

    summary = {}
    errors = []
    boards_for_md = {}

    for config in CONFIGS:
        print("\n=== %s" % config, file=sys.stderr)
        try:
            url = "%s/%s/latest/0000.parquet" % (PARQUET_BASE, config)
            raw = http_get(url)
            table = pq.read_table(io.BytesIO(raw))
            rows = table.to_pylist()
            if not rows:
                raise ValueError("empty table")
            cols, publish_date, overall, slices, note = build_boards(config, rows)
            slug = slugify(config)
            fetched_at = now.isoformat()

            if config == "agent":
                dims = sorted(slices) if slices else ["overall"]
                models = []
                for m in overall:
                    models.append({
                        "rank": m["rank"],
                        "model": m["model"],
                        "vendor": m["vendor"],
                        "license": m["license"],
                        "scores": [{"name": "overall", "score": m["score"], "ci": m["ci"]}],
                        "sessions": m["votes"],
                    })
                payload = {"meta": {"leaderboard": "agent", "source_url": SOURCE_URL, "fetched_at": fetched_at,
                                     "last_updated": publish_date, "model_count": len(models), "dimensions": ["overall"]},
                           "models": models}
                problems = list(agent_validator.iter_errors(payload))
            else:
                payload = {"meta": {"leaderboard": slug, "source_url": SOURCE_URL, "fetched_at": fetched_at,
                                     "last_updated": publish_date, "model_count": len(overall)},
                           "models": overall}
                problems = list(lb_validator.iter_errors(payload))

            if problems:
                msg = "; ".join("%s: %s" % (p.json_path, p.message) for p in problems[:4])
                raise ValueError("schema validation failed: " + msg)

            (day_dir / (slug + ".json")).write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n")

            all_payload = {
                "meta": {"leaderboard": slug, "source_url": SOURCE_URL, "fetched_at": fetched_at,
                          "last_updated": publish_date, "rows": len(rows),
                          "categories": sorted(slices), "columns": {k: v for k, v in cols.items() if v}},
                "models": [dict(m, category=cat) for cat in sorted(slices) for m in slices[cat]],
            }
            (all_dir / (slug + ".json")).write_text(json.dumps(all_payload, indent=2, ensure_ascii=False) + "\n")

            summary[slug] = {"model_count": max(len(overall), 1), "rows": len(rows),
                             "categories": len(slices), "publish_date": publish_date,
                             # 分类名清单，前端据此渲染分类切换，无需先下全量文件
                             "category_list": sorted(slices)}
            if note:
                summary[slug]["note"] = note
            boards_for_md[slug] = {"meta": all_payload["meta"], "categories": sorted(slices), "overall": overall}
            print("  ok rows=%d overall=%d categories=%d date=%s" % (len(rows), len(overall), len(slices), publish_date), file=sys.stderr)
        except Exception as exc:
            print("  FAILED: %s" % exc, file=sys.stderr)
            errors.append({"leaderboard": config, "error": str(exc)})

    if not summary:
        print("ERROR: no board could be built", file=sys.stderr)
        sys.exit(1)

    index = {"date": date_str, "fetched_at": now.isoformat(), "leaderboards": summary, "errors": errors}
    idx_problems = list(idx_validator.iter_errors(index))
    if idx_problems:
        print("ERROR: index schema invalid: %s" % idx_problems[0].message, file=sys.stderr)
        sys.exit(1)
    (day_dir / "_index.json").write_text(json.dumps(index, indent=2, ensure_ascii=False) + "\n")

    (repo_root / "data" / "latest.json").write_text(json.dumps({"date": date_str, "path": date_str}, indent=2) + "\n")
    (repo_root / "BOARDS.md").write_text(render_boards_md(boards_for_md, now.isoformat()) + "\n")

    print("\nwrote %d boards, %d errors -> data/%s" % (len(summary), len(errors), date_str), file=sys.stderr)
    if errors:
        for e in errors:
            print("  %s: %s" % (e["leaderboard"], e["error"]), file=sys.stderr)
        sys.stdout.flush()
        sys.stderr.flush()
        os._exit(1)

    sys.stdout.flush()
    sys.stderr.flush()
    os._exit(0)


if __name__ == "__main__":
    main()
