from __future__ import annotations

from collections.abc import Generator
from pathlib import Path

import httpx
import numpy as np
import pytest
from fastapi.testclient import TestClient
from rasterio.io import MemoryFile  # type: ignore[import-untyped]
from rasterio.transform import from_bounds  # type: ignore[import-untyped]
from rasterio.warp import transform_bounds  # type: ignore[import-untyped]

from app.api import naip as naip_api
from app.api.naip import get_naip_client
from app.imagery import NaipClient
from app.main import create_app

VALID_BBOX = {
    "min_lon": -97.8290,
    "min_lat": 30.4870,
    "max_lon": -97.8288,
    "max_lat": 30.4872,
}


def service_payload(
    *,
    max_image_width: int = 4000,
    max_image_height: int = 4000,
) -> dict[str, object]:
    return {
        "name": "USGSNAIPPlus",
        "serviceDescription": "NAIP and high resolution orthoimagery",
        "spatialReference": {"wkid": 102100, "latestWkid": 3857},
        "pixelType": "U8",
        "bandCount": 4,
        "capabilities": "Image,Metadata,Catalog,Mensuration",
        "copyrightText": "USGS, USDA, The National Map: Orthoimagery.",
        "maxImageWidth": max_image_width,
        "maxImageHeight": max_image_height,
    }


def mocked_naip_app(
    tmp_path: Path,
    *,
    image_failure: BaseException | None = None,
    image_status: int = 200,
    max_image_width: int = 4000,
    max_image_height: int = 4000,
) -> tuple[TestClient, httpx.Client, list[httpx.Request]]:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        if request.url.path.endswith("/USGSNAIPPlus/ImageServer"):
            return httpx.Response(
                200,
                json=service_payload(
                    max_image_width=max_image_width,
                    max_image_height=max_image_height,
                ),
                request=request,
            )
        if request.url.path.endswith("/exportImage"):
            if image_failure is not None:
                raise image_failure
            if image_status != 200:
                return httpx.Response(image_status, request=request)

            params = request.url.params
            width, height = (int(value) for value in params["size"].split(","))
            min_lon, min_lat, max_lon, max_lat = (
                float(value) for value in params["bbox"].split(",")
            )
            bounds = transform_bounds(
                "EPSG:4326",
                "EPSG:3857",
                min_lon,
                min_lat,
                max_lon,
                max_lat,
                densify_pts=21,
            )
            transform = from_bounds(*bounds, width=width, height=height)
            with MemoryFile() as memory_file:
                with memory_file.open(
                    driver="GTiff",
                    width=width,
                    height=height,
                    count=4,
                    dtype="uint8",
                    crs="EPSG:3857",
                    transform=transform,
                ) as dataset:
                    dataset.write(np.full((4, height, width), 100, dtype="uint8"))
                body = bytes(memory_file.read())
            return httpx.Response(
                200,
                content=body,
                headers={"content-type": "image/tiff"},
                request=request,
            )
        return httpx.Response(404, request=request)

    http_client = httpx.Client(transport=httpx.MockTransport(handler))
    naip_client = NaipClient(
        client=http_client,
        storage_directory=tmp_path,
        target_resolution_web_mercator_meters_per_pixel=5.0,
    )

    def override_client() -> Generator[NaipClient, None, None]:
        yield naip_client

    application = create_app()
    application.dependency_overrides[get_naip_client] = override_client
    return TestClient(application), http_client, requests


def close_route_client(client: TestClient, http_client: httpx.Client) -> None:
    client.close()
    http_client.close()


def test_post_naip_acquires_and_returns_safe_structured_reference(tmp_path: Path) -> None:
    client, http_client, requests = mocked_naip_app(tmp_path)
    try:
        response = client.post("/api/imagery/naip", json=VALID_BBOX)
    finally:
        close_route_client(client, http_client)

    assert response.status_code == 201
    body = response.json()
    assert body["acquisition_status"] == "acquired"
    assert body["acquisition_id"].startswith("naip_")
    assert body["image_url"] == (
        f"/api/imagery/naip/{body['acquisition_id']}/image"
    )
    assert body["provider"] == "USGS"
    assert body["service_name"] == "USGSNAIPPlus"
    assert body["request_bbox"] == VALID_BBOX
    assert body["request_bbox_crs"] == "EPSG:4326"
    assert body["crs"] == "EPSG:3857"
    assert body["band_count"] == 4
    assert body["dtype"] == "uint8"
    assert body["width"] > 0
    assert body["height"] > 0
    assert body["bounds"]
    assert body["resolution"] == body["pixel_size"]
    assert body["attribution"] == "USGS, USDA, The National Map: Orthoimagery."
    assert "storage_path" not in body
    assert "image_path" not in body
    assert len(requests) == 2


@pytest.mark.parametrize(
    "bbox",
    [
        {**VALID_BBOX, "min_lon": "-97.8290"},
        {**VALID_BBOX, "min_lat": -91.0},
        {**VALID_BBOX, "max_lon": 181.0},
        {key: value for key, value in VALID_BBOX.items() if key != "max_lat"},
    ],
)
def test_post_naip_rejects_invalid_bbox(bbox: dict[str, object]) -> None:
    with TestClient(create_app()) as client:
        response = client.post("/api/imagery/naip", json=bbox)

    assert response.status_code == 422


@pytest.mark.parametrize(
    ("min_lon", "max_lon", "min_lat", "max_lat"),
    [(-97.0, -97.0, 30.0, 30.1), (-97.0, -97.1, 30.0, 30.1), (-97.0, -96.9, 30.2, 30.1)],
)
def test_post_naip_rejects_reversed_or_empty_coordinates(
    min_lon: float,
    max_lon: float,
    min_lat: float,
    max_lat: float,
) -> None:
    payload = {
        "min_lon": min_lon,
        "min_lat": min_lat,
        "max_lon": max_lon,
        "max_lat": max_lat,
    }
    with TestClient(create_app()) as client:
        response = client.post("/api/imagery/naip", json=payload)

    assert response.status_code == 422


def test_post_naip_maps_oversized_aoi(tmp_path: Path) -> None:
    client, http_client, requests = mocked_naip_app(
        tmp_path,
        max_image_width=1,
        max_image_height=1,
    )
    try:
        response = client.post("/api/imagery/naip", json=VALID_BBOX)
    finally:
        close_route_client(client, http_client)

    assert response.status_code == 413
    assert response.json()["detail"]["code"] == "naip_aoi_too_large"
    assert len(requests) == 1


@pytest.mark.parametrize(
    ("image_status", "expected_status", "expected_code"),
    [(500, 502, "naip_provider_http_error")],
)
def test_post_naip_maps_provider_acquisition_failure(
    tmp_path: Path,
    image_status: int,
    expected_status: int,
    expected_code: str,
) -> None:
    client, http_client, _ = mocked_naip_app(tmp_path, image_status=image_status)
    try:
        response = client.post("/api/imagery/naip", json=VALID_BBOX)
    finally:
        close_route_client(client, http_client)

    assert response.status_code == expected_status
    assert response.json()["detail"]["code"] == expected_code


def test_post_naip_maps_timeout_and_connection_errors(tmp_path: Path) -> None:
    client, http_client, _ = mocked_naip_app(
        tmp_path,
        image_failure=httpx.ReadTimeout("timed out"),
    )
    try:
        timeout_response = client.post("/api/imagery/naip", json=VALID_BBOX)
    finally:
        close_route_client(client, http_client)

    assert timeout_response.status_code == 504
    assert timeout_response.json()["detail"]["code"] == "naip_provider_timeout"

    client, http_client, _ = mocked_naip_app(
        tmp_path,
        image_failure=httpx.ConnectError("connection failed"),
    )
    try:
        connection_response = client.post("/api/imagery/naip", json=VALID_BBOX)
    finally:
        close_route_client(client, http_client)

    assert connection_response.status_code == 503
    assert connection_response.json()["detail"]["code"] == "naip_provider_unavailable"


def test_get_naip_image_serves_tiff_by_safe_identifier(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    acquisition_id = "naip_20260928T101112.123456Z"
    image_path = tmp_path / f"{acquisition_id}.tif"
    image_path.write_bytes(b"II*\x00mock-tiff")
    monkeypatch.setattr(naip_api, "DEFAULT_STORAGE_DIRECTORY", tmp_path)

    with TestClient(create_app()) as client:
        response = client.get(f"/api/imagery/naip/{acquisition_id}/image")

    assert response.status_code == 200
    assert response.headers["content-type"] == "image/tiff"
    assert response.headers["content-disposition"].startswith("inline;")
    assert response.content == b"II*\x00mock-tiff"


@pytest.mark.parametrize("acquisition_id", ["..", "../outside", "naip_bad", "C:\\temp"])
def test_get_naip_image_rejects_invalid_identifier(
    acquisition_id: str,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(naip_api, "DEFAULT_STORAGE_DIRECTORY", tmp_path)
    with TestClient(create_app()) as client:
        response = client.get(f"/api/imagery/naip/{acquisition_id}/image")

    assert response.status_code in {404, 422}