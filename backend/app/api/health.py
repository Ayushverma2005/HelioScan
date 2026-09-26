from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()


class HealthResponse(BaseModel):
    status: str


@router.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    """Liveness check. Does not touch the database, Ollama, or any external API."""
    return HealthResponse(status="ok")
