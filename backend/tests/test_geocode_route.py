import httpx
import pytest
from fastapi.testclient import TestClient

from app.api.geocode import get_geocoding_provider
from app.geocoding.providers import NominatimProvider
from app.geocoding.rate_limit import ApplicationRateLimiter
from app.main import create_app


def result_payload(
    *,
    lat: str = "28.5457",
    lon: str = "77.1928",
    display_name: str = "IIT Delhi, Hauz Khas, New Delhi, India",
) -> dict[str, object]:
    return {
        "place_id": 123,
        "osm_type": "way",
        "osm_id": 456,
        "lat": lat,
        "lon": lon,
        "display_name": display_name,
        "licence": "Data © OpenStreetMap contributors, ODbL 1.0.",
        "address": {"city": "New Delhi", "country": "India"},
    }


def route_client(
    response_handler: httpx.MockTransport,
) -> tuple[TestClient, httpx.Client]:
    http_client = httpx.Client(transport=response_handler)
    provider = NominatimProvider(
        client=http_client,
        rate_limiter=ApplicationRateLimiter(),
    )
    application = create_app()
    application.dependency_overrides[get_geocoding_provider] = lambda: provider
    return TestClient(application), http_client


def test_geocode_returns_flat_helioscan_result_contract() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=[result_payload()], request=request)

    client, http_client = route_client(httpx.MockTransport(handler))
    try:
        response = client.post("/api/geocode", json={"query": "IIT Delhi"})
    finally:
        client.close()
        http_client.close()

    assert response.status_code == 200
    assert response.json() == {
        "results": [
            {
                "display_name": "IIT Delhi, Hauz Khas, New Delhi, India",
                "latitude": 28.5457,
                "longitude": 77.1928,
                "address": {"city": "New Delhi", "country": "India"},
                "provider_metadata": {
                    "provider": "nominatim",
                    "attribution": "Data © OpenStreetMap contributors, ODbL 1.0.",
                    "license": "ODbL",
                    "attribution_url": "https://www.openstreetmap.org/copyright",
                    "provider_result_id": "way456",
                },
            }
        ]
    }


def test_geocode_returns_zero_results_without_creating_coordinates() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=[], request=request)

    client, http_client = route_client(httpx.MockTransport(handler))
    try:
        response = client.post("/api/geocode", json={"query": "unknown place"})
    finally:
        client.close()
        http_client.close()

    assert response.status_code == 200
    assert response.json() == {"results": []}


def test_geocode_returns_multiple_results() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json=[
                result_payload(display_name="First result"),
                result_payload(lat="28.6", lon="77.2", display_name="Second result"),
            ],
            request=request,
        )

    client, http_client = route_client(httpx.MockTransport(handler))
    try:
        response = client.post("/api/geocode", json={"query": "IIT"})
    finally:
        client.close()
        http_client.close()

    assert response.status_code == 200
    assert [result["display_name"] for result in response.json()["results"]] == [
        "First result",
        "Second result",
    ]


@pytest.mark.parametrize(
    "payload",
    [{"query": ""}, {"query": "   "}, {}, {"query": 123}, {"query": "IIT", "unexpected": True}],
)
def test_geocode_rejects_invalid_input(payload: dict[str, object]) -> None:
    application = create_app()
    with TestClient(application) as client:
        response = client.post("/api/geocode", json=payload)

    assert response.status_code == 422


@pytest.mark.parametrize("status_code", [400, 500])
def test_geocode_maps_provider_http_errors(status_code: int) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(status_code, request=request)

    client, http_client = route_client(httpx.MockTransport(handler))
    try:
        response = client.post("/api/geocode", json={"query": "IIT Delhi"})
    finally:
        client.close()
        http_client.close()

    assert response.status_code == 502
    assert response.json() == {
        "detail": {
            "code": "geocoding_provider_http_error",
            "message": "The geocoding provider rejected the search request.",
        }
    }


def test_geocode_maps_timeout_and_connection_errors() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("timed out", request=request)

    client, http_client = route_client(httpx.MockTransport(handler))
    try:
        response = client.post("/api/geocode", json={"query": "IIT Delhi"})
    finally:
        client.close()
        http_client.close()

    assert response.status_code == 504
    assert response.json()["detail"]["code"] == "geocoding_provider_timeout"

    def connection_handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("connection failed", request=request)

    client, http_client = route_client(httpx.MockTransport(connection_handler))
    try:
        response = client.post("/api/geocode", json={"query": "IIT Delhi"})
    finally:
        client.close()
        http_client.close()

    assert response.status_code == 503
    assert response.json()["detail"]["code"] == "geocoding_provider_unavailable"


@pytest.mark.parametrize(
    "body",
    [b"not json", [{"lat": "28.5", "lon": "77.2"}], [result_payload(lat="91")]],
)
def test_geocode_maps_malformed_provider_responses(body: object) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if isinstance(body, bytes):
            return httpx.Response(200, content=body, request=request)
        return httpx.Response(200, json=body, request=request)

    client, http_client = route_client(httpx.MockTransport(handler))
    try:
        response = client.post("/api/geocode", json={"query": "IIT Delhi"})
    finally:
        client.close()
        http_client.close()

    assert response.status_code == 502
    assert response.json()["detail"]["code"] == "geocoding_provider_invalid_response"
