from __future__ import annotations
from fastapi import Header, HTTPException
from app.config import settings

def require_api_key(x_api_key: str | None = Header(default=None, alias="X-API-Key")) -> None:
    expected = settings.effective_api_key
    if not expected:
        raise HTTPException(status_code=500, detail="Server misconfigured: LOOCIE_INTERNAL_KEY not set")
    if not x_api_key or x_api_key != expected:
        raise HTTPException(status_code=401, detail="Unauthorized")
