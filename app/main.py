from contextlib import asynccontextmanager
from fastapi import FastAPI
from dotenv import load_dotenv
from app.api.router import api_router
from app.config import get_settings
from app.core.vault import verify_vault

load_dotenv()

@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    if settings.is_production:
        verify_vault(strict=True)
    else:
        status = verify_vault(strict=False)
        if not status.is_valid:
            import warnings
            warnings.warn("[LOOCIE DEV] Vault not mounted.")
    yield

settings = get_settings()
app = FastAPI(
    title=settings.loocie_api_title,
    version=settings.loocie_api_version,
    debug=settings.loocie_debug,
    lifespan=lifespan,
)
app.include_router(api_router)
