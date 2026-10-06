"""M8 — JSONL event logger for the Jog MVP."""
import json
from datetime import datetime, timezone
from pathlib import Path


class Logger:
    def __init__(self, path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def log(self, session_id, participant_id, mode, task_id, event, payload=None):
        rec = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "session_id": session_id,
            "participant_id": participant_id,
            "mode": mode,
            "task_id": task_id,
            "event": event,
            "payload": payload or {},
        }
        try:
            with open(self.path, "a") as f:
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")
        except Exception:
            pass

    def read_all(self):
        if not self.path.exists():
            return []
        out = []
        for line in self.path.read_text().splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                out.append(json.loads(line))
            except Exception:
                continue
        return out

    def read_session(self, session_id):
        return [r for r in self.read_all() if r.get("session_id") == session_id]
