"""Nominatim adapter for the internal geocoding contract."""

from __future__ import annotations

import math
from types import TracebackType
from typing import Any, Self

import httpx
from pydantic import BaseModel, ConfigDict, StrictStr, TypeAdapter, ValidationError

from app.core.config import settings
from app.geocoding.errors import (
	GeocodingConnectionError,
	GeocodingHTTPError,
	GeocodingResponseError,
	GeocodingTimeoutError,
)
from app.geocoding.models import (
	GeocodingCandidate,
	GeocodingSearchRequest,
	GeoCoordinate,
	ProviderMetadata,
)
from app.geocoding.rate_limit import ApplicationRateLimiter

NOMINATIM_SEARCH_URL = "https://nominatim.openstreetmap.org/search"
NOMINATIM_USER_AGENT = "HelioScan/0.1 (Phase 3 geocoding client)"
OSM_ATTRIBUTION_URL = "https://www.openstreetmap.org/copyright"
_SHARED_NOMINATIM_RATE_LIMITER = ApplicationRateLimiter(
	settings.nominatim_min_interval_seconds
)


class NominatimResult(BaseModel):
	"""Validated subset of the Nominatim jsonv2 result shape."""

	model_config = ConfigDict(extra="ignore")

	lat: StrictStr
	lon: StrictStr
	display_name: StrictStr
	licence: StrictStr
	address: dict[str, StrictStr] | None = None
	place_id: int | None = None
	osm_type: StrictStr | None = None
	osm_id: int | None = None


NOMINATIM_RESULTS = TypeAdapter(list[NominatimResult])


class NominatimProvider:
	"""Translate Nominatim responses into provider-independent candidates."""

	def __init__(
		self,
		client: httpx.Client | None = None,
		timeout_seconds: float = 10.0,
		rate_limiter: ApplicationRateLimiter | None = None,
	) -> None:
		if not math.isfinite(timeout_seconds) or timeout_seconds <= 0:
			raise ValueError("timeout_seconds must be finite and greater than zero")
		self._owns_client = client is None
		self._client = client or httpx.Client(
			timeout=httpx.Timeout(timeout_seconds),
			headers={"User-Agent": NOMINATIM_USER_AGENT},
		)
		self._rate_limiter = rate_limiter or _SHARED_NOMINATIM_RATE_LIMITER

	def search(self, request: GeocodingSearchRequest) -> list[GeocodingCandidate]:
		"""Search Nominatim; an empty list is a valid zero-result response."""
		params = self._build_params(request)
		try:
			with self._rate_limiter.slot():
				response = self._client.get(
					NOMINATIM_SEARCH_URL,
					params=params,
					headers={"User-Agent": NOMINATIM_USER_AGENT},
				)
				response.raise_for_status()
		except httpx.TimeoutException as exc:
			raise GeocodingTimeoutError("geocoding provider request timed out") from exc
		except httpx.HTTPStatusError as exc:
			raise GeocodingHTTPError(exc.response.status_code) from exc
		except httpx.NetworkError as exc:
			raise GeocodingConnectionError("geocoding provider connection failed") from exc

		try:
			raw_results = NOMINATIM_RESULTS.validate_python(response.json())
		except (ValueError, ValidationError) as exc:
			message = "geocoding provider returned invalid JSON or data"
			raise GeocodingResponseError(message) from exc

		return [self._normalize_result(result) for result in raw_results]

	def close(self) -> None:
		if self._owns_client:
			self._client.close()

	def __enter__(self) -> Self:
		return self

	def __exit__(
		self,
		exc_type: type[BaseException] | None,
		exc_value: BaseException | None,
		traceback: TracebackType | None,
	) -> None:
		self.close()

	@staticmethod
	def _build_params(request: GeocodingSearchRequest) -> dict[str, Any]:
		params: dict[str, Any] = {"format": "jsonv2", "limit": request.limit}
		if request.query is not None:
			params["q"] = request.query
		else:
			assert request.structured is not None
			params.update(request.structured.model_dump(exclude_none=True))
		return params

	@staticmethod
	def _normalize_result(result: NominatimResult) -> GeocodingCandidate:
		try:
			latitude = float(result.lat)
			longitude = float(result.lon)
		except ValueError as exc:
			message = "geocoding provider returned non-numeric coordinates"
			raise GeocodingResponseError(message) from exc

		if not math.isfinite(latitude) or not math.isfinite(longitude):
			raise GeocodingResponseError("geocoding provider returned non-finite coordinates")
		if not -90 <= latitude <= 90 or not -180 <= longitude <= 180:
			raise GeocodingResponseError("geocoding provider returned out-of-range coordinates")

		return GeocodingCandidate(
			coordinate=GeoCoordinate(latitude=latitude, longitude=longitude),
			display_name=result.display_name,
			address=result.address,
			provider_metadata=ProviderMetadata(
				provider="nominatim",
				attribution=result.licence,
				license="ODbL",
				attribution_url=OSM_ATTRIBUTION_URL,
				provider_result_id=_provider_result_id(result),
			),
		)


def _provider_result_id(result: NominatimResult) -> str | None:
	if result.osm_type is not None and result.osm_id is not None:
		return f"{result.osm_type}{result.osm_id}"
	if result.place_id is not None:
		return str(result.place_id)
	return None
