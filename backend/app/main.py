import logging

from fastapi import FastAPI

from app.api.geocode import router as geocode_router
from app.api.health import router as health_router
from app.core.config import Settings, settings
from app.core.logging import configure_logging

logger = logging.getLogger(__name__)


def create_app(app_settings: Settings | None = None) -> FastAPI:
    """Build the FastAPI app. Makes no database, Ollama, or network connections."""
    cfg = app_settings or settings
    configure_logging(cfg.log_level)
    application = FastAPI(title=cfg.app_name)
    application.include_router(health_router)
    application.include_router(geocode_router)
    logger.info("%s app created (environment=%s)", cfg.app_name, cfg.environment)
    return application


app = create_app()
