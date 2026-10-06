"""
Purpose: single writer for BASE/data/pipeline_counts.json (counts used by the
         Discovery Engine sidebar and the deck). Thread-safe merge of keys.
Inputs:  keyword arguments (any JSON-serializable values).
Outputs: merged JSON file (created if missing), returns the merged dict.
"""
import json
import os
import pathlib
import threading

BASE = pathlib.Path(__file__).resolve().parent.parent
COUNTS_PATH = BASE / "data" / "pipeline_counts.json"
_lock = threading.Lock()


def update_counts(**kwargs):
    with _lock:
        data = {}
        if COUNTS_PATH.exists():
            try:
                data = json.loads(COUNTS_PATH.read_text())
                if not isinstance(data, dict):
                    data = {}
            except Exception:
                data = {}
        data.update(kwargs)
        COUNTS_PATH.parent.mkdir(parents=True, exist_ok=True)
        tmp = COUNTS_PATH.with_name(COUNTS_PATH.name + ".tmp")
        tmp.write_text(json.dumps(data, indent=2) + "\n")
        os.replace(tmp, COUNTS_PATH)
        return dict(data)


def read_counts():
    if not COUNTS_PATH.exists():
        return {}
    try:
        data = json.loads(COUNTS_PATH.read_text())
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}
