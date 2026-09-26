"""FastAPI route for deliberate geocoding searches."""

from collections.abc import Generator
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field, StrictStr, field_validator

from app.geocoding.errors import (
    GeocodingConnectionError,
    GeocodingHTTPError,
    GeocodingResponseError,
    GeocodingTimeoutError,
)
from app.geocoding.models import GeocodingCandidate, GeocodingSearchRequest, ProviderMetadata
from app.geocoding.providers import NominatimProvider

router = APIRouter(prefix="/api")


class GeocodeRequest(BaseModel):
    """HelioScan-owned request contract for a deliberate search."""

    model_config = ConfigDict(extra="forbid")

    query: StrictStr
    limit: int = Field(default=10, ge=1, le=40)

    @field_validator("query")
    @classmethod
    def require_query(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("query must not be empty")
        return normalized


class GeocodeResult(BaseModel):
    """HelioScan-owned candidate contract with flat coordinates."""

    model_config = ConfigDict(extra="forbid")

    display_name: StrictStr
    latitude: float
    longitude: float
    address: dict[str, StrictStr] | None = None
    provider_metadata: ProviderMetadata


class GeocodeResponse(BaseModel):
    """Response containing zero or more validated search candidates."""

    model_config = ConfigDict(extra="forbid")

    results: list[GeocodeResult]


def get_geocoding_provider() -> Generator[NominatimProvider, None, None]:
    """Create a provider for one request and close its HTTP client afterward."""
    provider = NominatimProvider()
    try:
        yield provider
    finally:
        provider.close()


@router.post("/geocode", response_model=GeocodeResponse)
def geocode(
    request: GeocodeRequest,
    provider: Annotated[NominatimProvider, Depends(get_geocoding_provider)],
) -> GeocodeResponse:
    """Search for an address or POI without exposing provider wire details."""
    try:
        candidates = provider.search(
            GeocodingSearchRequest(query=request.query, limit=request.limit)
        )
    except GeocodingHTTPError as exc:
        raise _provider_http_exception(
            status_code=502,
            code="geocoding_provider_http_error",
            message="The geocoding provider rejected the search request.",
        ) from exc
    except GeocodingTimeoutError as exc:
        raise _provider_http_exception(
            status_code=504,
            code="geocoding_provider_timeout",
            message="The geocoding provider did not respond in time.",
        ) from exc
    except GeocodingConnectionError as exc:
        raise _provider_http_exception(
            status_code=503,
            code="geocoding_provider_unavailable",
            message="The geocoding provider is unavailable.",
        ) from exc
    except GeocodingResponseError as exc:
        raise _provider_http_exception(
            status_code=502,
            code="geocoding_provider_invalid_response",
            message="The geocoding provider returned an invalid response.",
        ) from exc

    return GeocodeResponse(results=[_to_result(candidate) for candidate in candidates])


def _to_result(candidate: GeocodingCandidate) -> GeocodeResult:
    return GeocodeResult(
        display_name=candidate.display_name,
        latitude=candidate.coordinate.latitude,
        longitude=candidate.coordinate.longitude,
        address=candidate.address,
        provider_metadata=candidate.provider_metadata,
    )


def _provider_http_exception(status_code: int, code: str, message: str) -> HTTPException:
    return HTTPException(status_code=status_code, detail={"code": code, "message": message})
