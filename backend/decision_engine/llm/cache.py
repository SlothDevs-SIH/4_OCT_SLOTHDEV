"""Local response cache so the demo works offline. One JSON file per evidence packet."""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional


def packet_key(packet: dict, system_prompt: str) -> str:
    raw = json.dumps(packet, sort_keys=True, ensure_ascii=False) + "\n" + system_prompt
    return hashlib.sha256(raw.encode()).hexdigest()[:32]


class LLMCache:
    def __init__(self, directory: Path):
        self.dir = Path(directory)

    def get(self, key: str) -> Optional[dict]:
        path = self.dir / f"{key}.json"
        if not path.is_file():
            return None
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except ValueError:
            return None

    def put(self, key: str, response: str, provider: str, model: Optional[str], task: str) -> None:
        self.dir.mkdir(parents=True, exist_ok=True)
        entry = {"key": key, "task": task, "provider": provider, "model": model, "response": response,
                 "created_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat()}
        (self.dir / f"{key}.json").write_text(json.dumps(entry, indent=2, ensure_ascii=False) + "\n")
