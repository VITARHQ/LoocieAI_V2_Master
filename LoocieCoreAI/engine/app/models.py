from __future__ import annotations
from pydantic import BaseModel, Field
from typing import Literal, Optional, List, Dict, Any

Mode = Literal["text","voice"]

class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1)
    mode: Mode = "text"
    conversation_id: Optional[str] = None

class ChatResponse(BaseModel):
    reply: str
    citations: Optional[List[Dict[str, Any]]] = None
    warnings: Optional[List[str]] = None

class HealthResponse(BaseModel):
    status: str
    engine: str
    version: str
    env: str
    uptime_seconds: float
    warnings: Optional[List[str]] = None

class StatusResponse(BaseModel):
    engine: str
    model: str
    provider: str
    endpoint: str
    model_name: str
    last_error: Optional[str] = None

class DiagnosticsResponse(BaseModel):
    paths: Dict[str, str]
    settings: Dict[str, Any]
    status: StatusResponse
    recent_audit_events: List[Dict[str, Any]]
