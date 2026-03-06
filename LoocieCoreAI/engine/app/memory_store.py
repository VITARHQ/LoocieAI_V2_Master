from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List

@dataclass
class ConversationStore:
    max_messages: int
    conversations: Dict[str, List[dict]] = field(default_factory=dict)

    def append(self, cid: str, role: str, content: str) -> None:
        msgs = self.conversations.setdefault(cid, [])
        msgs.append({"role": role, "content": content})
        if len(msgs) > self.max_messages:
            self.conversations[cid] = msgs[-self.max_messages:]

    def get(self, cid: str) -> List[dict]:
        return self.conversations.get(cid, []).copy()
