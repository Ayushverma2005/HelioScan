import httpx
import pytest

from app.geocoding.errors import (
    GeocodingConnectionError,
    GeocodingHTTPError,
    GeocodingResponseError,
    GeocodingTimeoutError,
)
from app.geocoding.models import GeocodingSearchRequest
from app.geocoding.providers import (
    NOMINATIM_SEARCH_URL,
    NOMINATIM_USER_AGENT,
    NominatimProvider,
)
from app.geocoding.rate_limit import ApplicationRateLimiter


def result_payload(
    *,
    lat: str = "40.7128",
    lon: str = "-74.0060",
    display_name: str = "New York, NY, United States",
) -> dict[str, object]:
    return {
        "place_id": 123,
        "osm_type": "relation",
        "osm_id": 456,
        "lat": lat,
        "lon": lon,
        "display_name": display_name,
        "licence": "Data © OpenStreetMap contributors, ODbL 1.0.",
        "address": {"city": "New York", "country": "United States"},
        "type": "city",
    }


def provider_for(handler: httpx.MockTransport) -> tuple[NominatimProvider, httpx.Client]:
    client = httpx.Client(transport=handler)
    return NominatimProvider(client=client, rate_limiter=ApplicationRateLimiter()), client


def test_successful_single_result_normalizes_response_and_request() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert str(request.url) == f"{NOMINATIM_SEARCH_URL}?format=jsonv2&limit=10&q=New+York"
        assert request.headers["user-agent"] == NOMINATIM_USER_AGENT
        return httpx.Response(200, json=[result_payload()], request=request)

    provider, client = provider_for(httpx.MockTransport(handler))
    try:
        candidates = provider.search(GeocodingSearchRequest(query=" New York "))
    finally:
        client.close()

    assert len(candidates) == 1
    assert candidates[0].coordinate.latitude == 40.7128
    assert candidates[0].coordinate.longitude == -74.006
    assert candidates[0].display_name == "New York, NY, United States"
    assert candidates[0].provider_metadata.provider == "nominatim"
    assert candidates[0].provider_metadata.license == "ODbL"


def test_multiple_results_are_returned_as_normalized_candidates() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json=[
                result_payload(display_name="First result"),
                result_payload(lat="51.5074", lon="-0.1278", display_name="Second result"),
            ],
            request=request,
        )

    provider, client = provider_for(httpx.MockTransport(handler))
    try:
        candidates = provider.search(GeocodingSearchRequest(query="city"))
    finally:
        client.close()

    assert [candidate.display_name for candidate in candidates] == ["First result", "Second result"]
    assert candidates[1].coordinate.latitude == 51.5074


def test_zero_results_are_distinct_from_provider_failure() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=[], request=request)

    provider, client = provider_for(httpx.MockTransport(handler))
    try:
        candidates = provider.search(GeocodingSearchRequest(query="no matching place"))
    finally:
        client.close()

    assert candidates == []


@pytest.mark.parametrize("status_code", [400, 404, 429, 500, 503])
def test_http_errors_are_translated(status_code: int) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(status_code, request=request)

    provider, client = provider_for(httpx.MockTransport(handler))
    try:
        with pytest.raises(GeocodingHTTPError) as error:
            provider.search(GeocodingSearchRequest(query="place"))
    finally:
        client.close()

    assert error.value.status_code == status_code


def test_timeout_is_translated() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("timed out", request=request)

    provider, client = provider_for(httpx.MockTransport(handler))
    try:
        with pytest.raises(GeocodingTimeoutError):
            provider.search(GeocodingSearchRequest(query="place"))
    finally:
        client.close()


def test_connection_failure_is_translated() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("connection failed", request=request)

    provider, client = provider_for(httpx.MockTransport(handler))
    try:
        with pytest.raises(GeocodingConnectionError):
            provider.search(GeocodingSearchRequest(query="place"))
    finally:
        client.close()


def test_invalid_json_is_rejected() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=b"not json", request=request)

    provider, client = provider_for(httpx.MockTransport(handler))
    try:
        with pytest.raises(GeocodingResponseError):
            provider.search(GeocodingSearchRequest(query="place"))
    finally:
        client.close()


def test_malformed_result_is_rejected() -> None:
    malformed = result_payload()
    del malformed["display_name"]

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=[malformed], request=request)

    provider, client = provider_for(httpx.MockTransport(handler))
    try:
        with pytest.raises(GeocodingResponseError):
            provider.search(GeocodingSearchRequest(query="place"))
    finally:
        client.close()


@pytest.mark.parametrize(
    ("lat", "lon"),
    [("not-a-number", "-74.0060"), ("91", "-74.0060"), ("nan", "-74.0060"), ("40.7128", "181")],
)
def test_invalid_coordinates_are_rejected(lat: str, lon: str) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=[result_payload(lat=lat, lon=lon)], request=request)

    provider, client = provider_for(httpx.MockTransport(handler))
    try:
        with pytest.raises(GeocodingResponseError):
            provider.search(GeocodingSearchRequest(query="place"))
    finally:
        client.close()
