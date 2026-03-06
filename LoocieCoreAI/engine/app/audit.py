from __future__ import annotations
import json, time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

Severity = Literal["info","warn","error"]

@dataclass
class AuditLogger:
    filepath: Path

    def write(self, event: str, severity: Severity="info", **fields: Any) -> None:
        rec = {"ts": time.time(), "event": event, "severity": severity, **fields}
        with self.filepath.open("a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")

    def tail(self, n: int=50) -> list[dict[str, Any]]:
        if not self.filepath.exists():
            return []
        lines = self.filepath.read_text(encoding="utf-8").splitlines()
        out = []
        for line in lines[-n:]:
            try:
                out.append(json.loads(line))
            except Exception:
                pass
        return out
