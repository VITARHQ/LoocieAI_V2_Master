from fastapi import APIRouter
import os

router = APIRouter()

@router.get("/")
def root():
    return {"status": "ok", "app": "LoocieAI_V2_Master"}

@router.get("/info")
def info():
    return {
        "app": "LoocieAI_V2_Master",
        "version": "v2.1.0",
        "env": os.getenv("LOOCIE_ENV", "dev"),
    }