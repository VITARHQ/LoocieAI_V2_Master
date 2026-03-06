from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple
import httpx

@dataclass
class ModelHealth:
    online: bool
    error: Optional[str] = None

@dataclass
class OllamaClient:
    endpoint: str
    model: str
    connect_timeout: float
    read_timeout: float

    def _client(self) -> httpx.Client:
        return httpx.Client(timeout=httpx.Timeout(self.read_timeout, connect=self.connect_timeout))

    def health(self) -> ModelHealth:
        try:
            with self._client() as c:
                r = c.get(f"{self.endpoint}/api/tags")
                r.raise_for_status()
            return ModelHealth(True)
        except Exception as e:
            return ModelHealth(False, str(e))

    def chat(self, messages: List[Dict[str, str]]) -> Tuple[str, Optional[str]]:
        payload = {"model": self.model, "messages": messages, "stream": False}
        try:
            with self._client() as c:
                r = c.post(f"{self.endpoint}/api/chat", json=payload)
                r.raise_for_status()
                data = r.json()
            reply = (data.get("message") or {}).get("content") or ""
            return (reply, None) if reply else ("", "Empty reply from model")
        except Exception as e:
            return "", str(e)
