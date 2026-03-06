from __future__ import annotations
import time
from fastapi import FastAPI, Depends, HTTPException
from app.config import settings
from app.audit import AuditLogger
from app.security import require_api_key
from app.models import ChatRequest, ChatResponse, HealthResponse, StatusResponse, DiagnosticsResponse
from app.memory_store import ConversationStore
from app.model_clients import OllamaClient

BOOT_TS = time.time()
app = FastAPI(title="LoocieCoreAI Core Engine", version=settings.engine_version)

settings.ensure_dirs()
AUDIT_PATH = settings.logs_dir / "audit.jsonl"
audit = AuditLogger(filepath=AUDIT_PATH)
memory = ConversationStore(max_messages=settings.memory_max_messages)

MODEL = OllamaClient(
    endpoint=settings.model_endpoint.rstrip("/"),
    model=settings.model_name,
    connect_timeout=settings.connect_timeout_seconds,
    read_timeout=settings.read_timeout_seconds,
)

def _is_protected_intent(text: str) -> bool:
    t = text.lower()
    keys = ["delete","remove","erase","export","pay","payment","send email","email ","text ","sms ","change settings","reconfigure"]
    return any(k in t for k in keys)

def _protected_gate(req: ChatRequest):
    if not _is_protected_intent(req.message):
        return None
    warns = []
    if req.mode != "text":
        warns.append("Protected action requires mode='text'.")
    if not settings.loocie_text_unlock:
        warns.append("Protected action blocked: LOOCIE_TEXT_UNLOCK not set in .env (build/test).")
    if "CONFIRM" not in req.message:
        warns.append("Protected action requires explicit confirmation: include 'CONFIRM'.")
    return warns if warns else None

@app.on_event("startup")
def _startup():
    audit.write("core_boot", env=settings.env, engine=settings.engine_name, version=settings.engine_version)
    if settings.warmup_on_start:
        h = MODEL.health()
        audit.write("model_warmup_ok" if h.online else "model_warmup_failed", severity=("info" if h.online else "warn"), error=h.error)

@app.get("/health", response_model=HealthResponse)
def health():
    warnings = []
    if not settings.effective_api_key:
        warnings.append("LOOCIE_INTERNAL_KEY not set. Secured endpoints will fail closed.")
    return HealthResponse(
        status="ok",
        engine=settings.engine_name,
        version=settings.engine_version,
        env=settings.env,
        uptime_seconds=max(0.0, time.time() - BOOT_TS),
        warnings=warnings or None,
    )

@app.get("/status", response_model=StatusResponse, dependencies=[Depends(require_api_key)])
def status():
    h = MODEL.health()
    return StatusResponse(
        engine="online",
        model=("online" if h.online else "offline"),
        provider="ollama",
        endpoint=settings.model_endpoint,
        model_name=settings.model_name,
        last_error=h.error,
    )

@app.post("/chat", response_model=ChatResponse, dependencies=[Depends(require_api_key)])
def chat(req: ChatRequest):
    gate = _protected_gate(req)
    if gate:
        audit.write("protected_action_requested", severity="warn", mode=req.mode, warnings=gate)
        return ChatResponse(reply="Protected action blocked by Core policy gate.", warnings=gate)

    sys_prompt = (
        "You are LoocieCoreAI Companion. "
        "Pleasant, helpful general assistant with no job title. "
        "Be concise and practical. "
        "Do not claim access to private persona drives."
    )
    msgs = [{"role":"system","content":sys_prompt}]
    if req.conversation_id:
        msgs += memory.get(req.conversation_id)
    msgs.append({"role":"user","content":req.message})

    reply, err = MODEL.chat(msgs)
    if err:
        audit.write("chat_failed", severity="error", error=err)
        raise HTTPException(status_code=502, detail=f"Model call failed: {err}")

    if req.conversation_id:
        memory.append(req.conversation_id, "user", req.message)
        memory.append(req.conversation_id, "assistant", reply)

    audit.write("chat_ok", mode=req.mode, conversation_id=req.conversation_id or "")
    return ChatResponse(reply=reply)

@app.get("/diagnostics", response_model=DiagnosticsResponse, dependencies=[Depends(require_api_key)])
def diagnostics():
    st = status()
    recent = audit.tail(50)
    audit.write("diagnostics_viewed")
    return DiagnosticsResponse(
        paths={
            "app_support_dir": str(settings.app_support_dir),
            "logs_dir": str(settings.logs_dir),
            "audit_log": str(AUDIT_PATH),
        },
        settings=settings.redact(),
        status=st,
        recent_audit_events=recent,
    )
