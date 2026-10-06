"""Re-screen images deleted for QUERY-level irrelevance with an EVENT-level
(less strict) standard: the synthetic library needs photos that could plausibly
belong to the life event, not exact query matches. Safety deletions stay.
Then cap each event at its target (drop newest surplus). Resume-safe."""
import csv
import json
import sys
from pathlib import Path

import pandas as pd

BASE = Path(__file__).resolve().parent.parent
LIB = BASE / "library"
IMAGES = LIB / "images"
SCR_LOG = BASE / "cache" / "m1_screen_relaxed.jsonl"
SAFETY = ("close-up", "portrait", "child", "watermark", "logo", "nudity",
          "suggestive", "graphic", "violent", "identifiable")

def ts_log(msg):
    from datetime import datetime, timezone
    print(f"{datetime.now(timezone.utc).astimezone().isoformat(timespec='seconds')} {msg}", flush=True)

def main():
    raw = pd.read_csv(LIB / "images_raw.csv")
    ev = {r["event_id"]: r for r in csv.DictReader(open(LIB / "events.csv"))}
    ev_name = {r["event_id"]: r["name"] for r in csv.DictReader(open(LIB / "events.csv"))}

    is_safety = raw["delete_reason"].fillna("").str.lower().apply(
        lambda r: any(k in r for k in SAFETY))
    todo = raw[raw["deleted"].fillna(False).astype(bool) & ~is_safety]
    ts_log(f"relevance-deleted candidates: {len(todo)}")

    sys.path.insert(0, str(BASE / "code"))
    import llm_helper
    from pydantic import BaseModel

    class ScreenDecision(BaseModel):
        delete: bool = False
        reason: str = ""

    cached = {}
    if SCR_LOG.exists():
        for line in SCR_LOG.read_text().splitlines():
            line = line.strip()
            if line:
                try:
                    r = json.loads(line)
                    cached[r["img_id"]] = r
                except Exception:
                    pass

    todo2 = [r for _, r in todo.iterrows() if r["img_id"] not in cached]
    ts_log(f"todo: {len(todo2)} (cached {len(cached)})")

    def screen_one(r):
        user = (f"The photo was fetched for the life event \"{ev_name[r['event_id']]}\" "
                f"(search query: \"{r['query']}\" — treat the query as a hint only). "
                "This is a SYNTHETIC personal photo library for a research demo; photos "
                "need to be usable as memories from that life event. "
                "Judge ONLY what is visible. Return JSON: {\"delete\": true|false, "
                "\"reason\": \"<=12 words; empty if keep\"}. "
                "delete=true ONLY if: nudity or graphic/violent content; a close-up or "
                "clearly identifiable portrait of a private individual (crowd shots, "
                "landmark and scene shots with small people are fine); a close-up of a "
                "child's face; a logo/watermark/advertisement dominates the frame; or it "
                "is clearly not a real photograph (illustration, 3D render, text graphic, "
                "stock-art). delete=false otherwise, even if generic or only loosely "
                "matching the query.")
        res = llm_helper.llm_json_image("You screen stock photos for a synthetic personal photo-library demo.",
                                        user, IMAGES / r["filename"],
                                        schema_model=ScreenDecision, profile="local")
        if "_error" in res:
            return r["img_id"], {"delete": True, "reason": "screen error; keep deleted", "_error": res["_error"]}
        return r["img_id"], {"delete": bool(res.get("delete", False)),
                             "reason": str(res.get("reason", ""))[:120]}

    if todo2:
        results = llm_helper.llm_json_batch(todo2, screen_one, workers=8)
        with open(SCR_LOG, "a") as f:
            for r, res in zip(todo2, results):
                if res is None:
                    res = {"delete": True, "reason": "batch None"}
                if isinstance(res, tuple):
                    res = res[1]
                if not isinstance(res, dict):
                    res = {"delete": True, "reason": f"bad result {type(res).__name__}"}
                cached[r["img_id"]] = res
                f.write(json.dumps({"img_id": r["img_id"], **res}) + "\n")

    # apply: relevance-deleted rows with relaxed verdict keep=False -> un-delete
    n_undeleted = 0
    for i, r in raw.iterrows():
        if r["deleted"] and not is_safety.iloc[i] and r["img_id"] in cached:
            if not cached[r["img_id"]].get("delete"):
                raw.at[i, "deleted"] = False
                raw.at[i, "delete_reason"] = ""
                n_undeleted += 1
    ts_log(f"un-deleted by relaxed screen: {n_undeleted}")

    # cap each event at its target; drop surplus starting from newest img_id
    n_capped = 0
    for eid, target in ev.items():
        sub = raw[(raw["event_id"] == eid) & ~raw["deleted"].fillna(False).astype(bool)]
        over = len(sub) - int(target["target_count"])
        if over > 0:
            sub_sorted = sub.sort_values("img_id", ascending=False)
            for i in sub_sorted.index[:over]:
                raw.at[i, "deleted"] = True
                raw.at[i, "delete_reason"] = "over_target"
                n_capped += 1
    ts_log(f"capped over-target surplus: {n_capped}")

    raw.to_csv(LIB / "images_raw.csv", index=False,
               quoting=csv.QUOTE_MINIMAL)
    kept = raw[~raw["deleted"].fillna(False).astype(bool)]
    g = kept.groupby("event_id").size()
    for eid in ev:
        t = int(ev[eid]["target_count"])
        k = int(g.get(eid, 0))
        flag = "" if k >= 0.6 * t else "  <-- BELOW 60%"
        print(f"  {eid}: {k}/{t}{flag}", flush=True)
    print(f"TOTAL non-deleted: {len(kept)}", flush=True)
    print("DONE rescreen_relaxed", flush=True)

if __name__ == "__main__":
    main()
