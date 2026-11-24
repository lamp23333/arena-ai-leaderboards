#!/usr/bin/env python3
"""Fetch Artificial Analysis Intelligence Index data.

Two paths:

1. Official Data API (preferred, needs AA_API_KEY - free tier works)
     GET https://artificialanalysis.ai/api/v2/language/models
     header: x-api-key: <key>
   Docs: https://artificialanalysis.ai/data-api
   Note: the old /api/v2/data/* endpoints were retired on 2026-11-04 (410 Gone).

2. No key: scrape the RSC payload embedded in https://artificialanalysis.ai/models/comparisons
   Fewer models, but keeps the pipeline alive without a key.

Output:
  data-aa/latest.json      { date, source, fetched_at, doc, models: [...] }
  data-aa/<date>.json      same, daily archive
"""

import datetime
import json
import os
import re
import sys
import urllib.error
import urllib.request

API_URL = "https://artificialanalysis.ai/api/v2/language/models"
PAGE_URL = "https://artificialanalysis.ai/models/comparisons"
DOC_URL = "https://artificialanalysis.ai/data-api"
OUT_DIR = "data-aa"
UA = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Accept-Language": "en-US,en;q=0.9",
}

VENDOR_RULES = [
    ("claude", "anthropic"),
    ("gpt", "openai"), ("o1", "openai"), ("o3", "openai"), ("o4", "openai"),
    ("o5", "openai"), ("codex", "openai"), ("chatgpt", "openai"), ("sora", "openai"),
    ("gemini", "google"), ("gemma", "google"), ("veo", "google"), ("imagen", "google"),
    ("grok", "xai"),
    ("deepseek", "deepseek"),
    ("qwen", "alibaba"), ("qwq", "alibaba"), ("wan", "alibaba"),
    ("ling", "inclusionai"),
    ("glm", "zai"),
    ("kimi", "moonshot"),
    ("mimo", "xiaomi"),
    ("minimax", "minimax"), ("hailuo", "minimax"),
    ("mistral", "mistral"), ("magistral", "mistral"), ("devstral", "mistral"),
    ("pixtral", "mistral"), ("voxtral", "mistral"), ("codestral", "mistral"),
    ("llama", "meta"),
    ("nemotron", "nvidia"),
    ("command", "cohere"),
    ("ernie", "baidu"),
    ("hunyuan", "tencent"),
    ("step", "stepfun"),
    ("doubao", "bytedance"), ("seed", "bytedance"), ("kling", "kling"),
    ("phi", "microsoft"),
    ("olmo", "allenai"),
    ("granite", "ibm"),
    ("jamba", "ai21"),
    ("mercury", "inception"),
    ("inkling", "thinky"),
    ("longcat", "meituan"),
    ("mochi", "genmo"),
    ("kandinsky", "sber"),
    ("skyreels", "skyreel"),
    ("hidream", "hidream"),
    ("lucid", "leonardo-ai"),
    ("happyhorse", "aorizon"),
    ("vidu", "shengshu"),
    ("yuanshi", "shengshu"),
]

INDEX_KEYS = ("intelligenceIndex", "intelligence_index")


def fetch(url, extra=None, timeout=60):
    headers = dict(UA)
    if extra:
        headers.update(extra)
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status, resp.read()
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read()


def rsc_blob(html):
    chunks = re.findall(r'self\.__next_f\.push\(\[1,"(.*?)"\]\)', html, re.S)
    parts = []
    for chunk in chunks:
        try:
            parts.append(json.loads('"' + chunk + '"'))
        except Exception:
            continue
    return "".join(parts)


def deep_get(obj, names):
    if isinstance(obj, dict):
        for key, value in obj.items():
            if key in names and isinstance(value, (int, float)):
                return value
        for value in obj.values():
            found = deep_get(value, names)
            if found is not None:
                return found
    elif isinstance(obj, list):
        for value in obj:
            found = deep_get(value, names)
            if found is not None:
                return found
    return None


def collect_model_dicts(obj, out, depth=0):
    """Recursively collect every dict that carries an intelligence index."""
    if depth > 12:
        return
    if isinstance(obj, dict):
        if any(key in obj for key in INDEX_KEYS):
            out.append(obj)
            return
        for value in obj.values():
            collect_model_dicts(value, out, depth + 1)
    elif isinstance(obj, list):
        for value in obj:
            collect_model_dicts(value, out, depth + 1)


def pick(obj, *names):
    for name in names:
        value = obj.get(name)
        if value not in (None, ""):
            return value
    return None


def vendor_of(slug, name, obj):
    explicit = pick(obj, "vendor", "model_creator", "creator", "creator_name", "provider")
    if isinstance(explicit, dict):
        explicit = explicit.get("name") or explicit.get("slug")
    if isinstance(explicit, str) and explicit.strip():
        return explicit.strip().lower()
    lowered = ((slug or "") + " " + (name or "")).lower()
    for prefix, vendor in VENDOR_RULES:
        if lowered.startswith(prefix) or (" " + prefix) in lowered:
            return vendor
    return ""


def normalize(obj):
    slug = pick(obj, "slug", "model_slug", "shortName", "name")
    if not slug or not isinstance(slug, str):
        return None
    name = pick(obj, "shortName", "name", "model_name", "short_name") or slug
    index = pick(obj, *INDEX_KEYS)
    if not isinstance(index, (int, float)):
        index = deep_get(obj, set(INDEX_KEYS))
    if not isinstance(index, (int, float)):
        return None
    price_in = pick(obj, "price1mInputTokens", "price_1m_input_tokens", "price_1m_input")
    price_out = pick(obj, "price1mOutputTokens", "price_1m_output_tokens", "price_1m_output")
    speed = pick(obj, "outputSpeed", "median_output_tokens_per_second", "output_tokens_per_second")
    effort = pick(obj, "effort")
    if isinstance(effort, dict):
        effort = effort.get("label") or effort.get("slug")
    return {
        "model": slug,
        "model_display": name,
        "vendor": vendor_of(slug, name, obj),
        "index": round(float(index), 2),
        "price_in": round(float(price_in), 3) if isinstance(price_in, (int, float)) else None,
        "price_out": round(float(price_out), 3) if isinstance(price_out, (int, float)) else None,
        "speed": round(float(speed), 1) if isinstance(speed, (int, float)) else None,
        "open_weights": obj.get("isOpenWeights") if "isOpenWeights" in obj else None,
        "release_date": pick(obj, "releaseDate", "release_date"),
        "context": pick(obj, "contextWindowTokens"),
        "effort": effort,
        "name_full": pick(obj, "name"),
    }


def harvest(blob, decoder, seen):
    """Pull models out of the RSC payload.

    Model objects live inside JSON arrays (e.g. "models":[{...},{...}]).
    Decoding a whole array at once is far more reliable than guessing
    object boundaries, so try every array first, then fall back to
    walking backwards from each intelligence-index key.
    """
    for m in re.finditer(r'"[A-Za-z_]{2,24}"\s*:\s*\[', blob):
        start = blob.find("[", m.start())
        if start < 0:
            continue
        try:
            arr, _end = decoder.raw_decode(blob, start)
        except Exception:
            continue
        if not isinstance(arr, list) or len(arr) < 2:
            continue
        bucket = []
        collect_model_dicts(arr, bucket)
        for one in bucket:
            item = normalize(one)
            if item:
                seen[item["model"]] = item

    if seen:
        return

    for m in re.finditer(r'"intelligence[_A-Za-z]*"\s*:', blob):
        pos = m.start()
        start = blob.rfind("{", max(0, pos - 6000), pos)
        tries = 0
        while start >= 0 and tries < 8:
            tries += 1
            try:
                obj, _end = decoder.raw_decode(blob, start)
            except Exception:
                start = blob.rfind("{", max(0, pos - 6000), start)
                continue
            bucket = []
            collect_model_dicts(obj, bucket)
            for one in bucket:
                item = normalize(one)
                if item:
                    seen[item["model"]] = item
            break


def collect_from_page():
    status, body = fetch(PAGE_URL)
    if status != 200:
        raise RuntimeError("page http " + str(status))
    blob = rsc_blob(body.decode("utf-8", "replace"))
    if not blob:
        raise RuntimeError("empty rsc payload")
    seen = {}
    harvest(blob, json.JSONDecoder(), seen)
    return list(seen.values()), len(blob)


def collect_from_api(key):
    status, body = fetch(API_URL, {"x-api-key": key})
    text = body.decode("utf-8", "replace")
    if status != 200:
        raise RuntimeError("api http " + str(status) + " " + text[:200])
    payload = json.loads(text)
    rows = payload.get("data") if isinstance(payload, dict) else payload
    if not isinstance(rows, list):
        raise RuntimeError("unexpected api payload keys: " + str(list(payload)[:8]))
    if rows:
        print("api sample keys:", list(rows[0])[:20])
    out = {}
    for obj in rows:
        if isinstance(obj, dict):
            item = normalize(obj)
            if item:
                out[item["model"]] = item
    return list(out.values()), len(text)


def main():
    key = (os.environ.get("AA_API_KEY") or "").strip()
    source = "page"
    models = []
    detail = ""

    if key:
        try:
            models, detail = collect_from_api(key)
            source = "api"
        except Exception as exc:
            print("api failed:", type(exc).__name__, str(exc)[:200])
            models = []

    if not models:
        models, detail = collect_from_page()
        source = "page"

    if not models:
        print("no models parsed")
        return 1

    models.sort(key=lambda item: item["index"], reverse=True)
    for rank, item in enumerate(models, 1):
        item["rank"] = rank

    today = datetime.datetime.utcnow().strftime("%Y-%m-%d")
    payload = {
        "date": today,
        "source": source,
        "fetched_at": datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
        "doc": DOC_URL,
        "model_count": len(models),
        "models": models,
    }

    os.makedirs(OUT_DIR, exist_ok=True)
    text = json.dumps(payload, ensure_ascii=False, indent=1) + "\n"
    with open(os.path.join(OUT_DIR, "latest.json"), "w", encoding="utf-8") as fh:
        fh.write(text)
    with open(os.path.join(OUT_DIR, today + ".json"), "w", encoding="utf-8") as fh:
        fh.write(text)

    print("source:", source, "| models:", len(models), "| payload:", detail)
    for item in models[:5]:
        print("  ", item["rank"], item["model_display"], item["vendor"], item["index"])
    print("wrote", OUT_DIR + "/latest.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
