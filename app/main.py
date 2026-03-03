from contextlib import asynccontextmanager
from fastapi import FastAPI
from dotenv import load_dotenv

load_dotenv()

from app.config import get_settings
from app.logging import setup_logging, get_logger
from app.api.router import api_router
from app.core.vault import verify_vault

settings = get_settings()
setup_logging(level="DEBUG" if settings.is_dev else "INFO")
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("[ENGINE] Loocie AI V2 starting up - env=%s", settings.loocie_env)
    if settings.is_production:
        verify_vault(strict=True)
        logger.info("[VAULT] Business Vault verified")
    else:
        status = verify_vault(strict=False)
        if not status.is_valid:
            logger.warning("[VAULT] Not mounted - vault features disabled in dev")
        else:
            logger.info("[VAULT] Business Vault verified at %s", status.vault_path)
    logger.info("[ENGINE] Startup complete - ready to serve requests")
    yield
    logger.info("[ENGINE] Loocie AI shutting down")


app = FastAPI(
    title=settings.loocie_api_title,
    version=settings.loocie_api_version,
    debug=settings.loocie_debug,
    lifespan=lifespan,
)

app.include_router(api_router)
