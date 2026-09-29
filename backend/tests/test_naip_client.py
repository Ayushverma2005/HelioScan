from __future__ import annotations

import json
from collections.abc import Callable
from pathlib import Path
from typing import Any, cast

import httpx
import numpy as np
import pytest
import rasterio  # type: ignore[import-untyped]
from pydantic import ValidationError
from rasterio.io import MemoryFile  # type: ignore[import-untyped]
from rasterio.transform import from_bounds  # type: ignore[import-untyped]
from rasterio.warp import transform_bounds  # type: ignore[import-untyped]

from app.imagery.client import (
    DEFAULT_STORAGE_DIRECTORY,
    NaipClient,
)
from app.imagery.errors import (
    NaipAreaTooLargeError,
    NaipConnectionError,
    NaipHTTPError,
    NaipResponseError,
    NaipTimeoutError,
)
from app.imagery.models import GeographicBBox

TEST_BBOX: dict[str, object] = {
    "min_lon": -97.8290,
    "min_lat": 30.4870,
    "max_lon": -97.8288,
    "max_lat": 30.4872,
}


def service_payload(
    *, max_image_width: int = 4000, max_image_height: int = 4000
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
        "defaultMosaicMethod": "ByAttribute",
        "sortField": "Year",
        "sortValue": "3000",
        "sortAscending": True,
        "mosaicOperator": "First",
    }


def tiny_geotiff(
    width: int,
    height: int,
    bounds: tuple[float, float, float, float],
    *,
    count: int = 4,
    dtype: str = "uint8",
    crs: str = "EPSG:3857",
    transform: Any | None = None,
    value: int = 100,
    all_masked: bool = False,
) -> bytes:
    data_transform = transform or from_bounds(*bounds, width=width, height=height)
    with MemoryFile() as memory_file:
        with memory_file.open(
            driver="GTiff",
            width=width,
            height=height,
            count=count,
            dtype=dtype,
            crs=crs,
            transform=data_transform,
        ) as dataset:
            dataset.write(np.full((count, height, width), value, dtype=dtype))
            if all_masked:
                dataset.write_mask(np.zeros((height, width), dtype="uint8"))
        return bytes(memory_file.read())


def make_transport(
    *,
    image_status: int = 200,
    image_content_type: str | None = "image/tiff",
    image_body_factory: Callable[[httpx.Request], bytes] | None = None,
    service_data: dict[str, object] | None = None,
    image_failure: BaseException | None = None,
) -> tuple[httpx.Client, list[httpx.Request]]:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        if request.url.path == "/arcgis/rest/services/USGSNAIPPlus/ImageServer":
            return httpx.Response(200, json=service_data or service_payload(), request=request)
        if request.url.path.endswith("/exportImage"):
            if image_failure is not None:
                raise image_failure
            body = (
                image_body_factory(request)
                if image_body_factory is not None
                else default_image_body(request)
            )
            headers = {}
            if image_content_type is not None:
                headers["content-type"] = image_content_type
            return httpx.Response(image_status, content=body, headers=headers, request=request)
        return httpx.Response(404, request=request)

    return httpx.Client(transport=httpx.MockTransport(handler)), requests


def default_image_body(request: httpx.Request) -> bytes:
    params = request.url.params
    width, height = (int(value) for value in params["size"].split(","))
    min_lon, min_lat, max_lon, max_lat = (
        float(value) for value in params["bbox"].split(",")
    )
    projected = transform_bounds(
        "EPSG:4326",
        "EPSG:3857",
        min_lon,
        min_lat,
        max_lon,
        max_lat,
        densify_pts=21,
    )
    return tiny_geotiff(width, height, projected)


def client_for(
    tmp_path: Path,
    *,
    target_resolution_web_mercator_meters_per_pixel: float = 5.0,
    max_response_bytes: int = 1024 * 1024,
    **transport_options: Any,
) -> tuple[NaipClient, httpx.Client, list[httpx.Request]]:
    http_client, requests = make_transport(**transport_options)
    naip_client = NaipClient(
        client=http_client,
        storage_directory=tmp_path,
        target_resolution_web_mercator_meters_per_pixel=(
            target_resolution_web_mercator_meters_per_pixel
        ),
        max_response_bytes=max_response_bytes,
    )
    return naip_client, http_client, requests


def test_valid_bbox_accepts_decimal_wgs84_coordinates() -> None:
    bbox = GeographicBBox.model_validate(TEST_BBOX)

    assert bbox.min_lon == TEST_BBOX["min_lon"]
    assert bbox.min_lat == TEST_BBOX["min_lat"]
    assert bbox.max_lon == TEST_BBOX["max_lon"]
    assert bbox.max_lat == TEST_BBOX["max_lat"]


@pytest.mark.parametrize(
    "bbox",
    [
        {**TEST_BBOX, "min_lon": -97.0, "max_lon": -97.0},
        {**TEST_BBOX, "min_lat": 30.0, "max_lat": 30.0},
        {**TEST_BBOX, "min_lon": -181.0},
        {**TEST_BBOX, "max_lat": 91.0},
        {**TEST_BBOX, "min_lon": "-97.8290"},
        {**TEST_BBOX, "max_lat": float("nan")},
        {**TEST_BBOX, "min_lat": True},
        {key: value for key, value in TEST_BBOX.items() if key != "max_lat"},
        {**TEST_BBOX, "extra": 1},
    ],
)
def test_invalid_bbox_is_rejected(bbox: dict[str, object]) -> None:
    with pytest.raises(ValidationError):
        GeographicBBox.model_validate(bbox)


def test_success_requests_explicit_parameters_and_persists_four_band_raster(
    tmp_path: Path,
) -> None:
    naip_client, http_client, requests = client_for(tmp_path)
    try:
        result = naip_client.acquire(TEST_BBOX)
    finally:
        http_client.close()

    image_request = requests[1]
    params = image_request.url.params
    assert requests[0].url.params["f"] == "json"
    assert params["bboxSR"] == "4326"
    assert params["imageSR"] == "3857"
    assert params["bbox"] == "-97.829,30.487,-97.8288,30.4872"
    assert params["format"] == "tiff"
    assert params["pixelType"] == "U8"
    assert params["bandIds"] == "0,1,2,3"
    assert params["interpolation"] == "RSP_BilinearInterpolation"
    assert params["compression"] == "LZ77"
    assert params["adjustAspectRatio"] == "false"
    assert params["f"] == "image"
    assert result.image_path.exists()
    assert result.metadata_path.exists()
    assert result.image_path.parent == tmp_path

    with rasterio.open(result.image_path) as dataset:
        assert dataset.width == result.metadata.width
        assert dataset.height == result.metadata.height
        assert dataset.count == 4
        assert dataset.dtypes == ("uint8",) * 4
        assert dataset.crs.to_epsg() == 3857

    sidecar = json.loads(result.metadata_path.read_text(encoding="utf-8"))
    assert sidecar["service_name"] == "USGSNAIPPlus"
    assert sidecar["requested_bbox_crs"] == "EPSG:4326"
    assert sidecar["output_crs"] == "EPSG:3857"
    assert sidecar["attribution"] == "USGS, USDA, The National Map: Orthoimagery."
    assert sidecar["band_count"] == 4
    assert sidecar["dtype"] == "uint8"
    assert sidecar["response_content_type"] == "image/tiff"


def test_tiff_signature_is_accepted_without_content_type(tmp_path: Path) -> None:
    naip_client, http_client, _ = client_for(tmp_path, image_content_type=None)
    try:
        result = naip_client.acquire(TEST_BBOX)
    finally:
        http_client.close()

    assert result.image_path.is_file()


@pytest.mark.parametrize("status_code", [400, 401, 403, 404, 429, 500, 503])
def test_http_error_statuses_are_reported(tmp_path: Path, status_code: int) -> None:
    naip_client, http_client, _ = client_for(tmp_path, image_status=status_code)
    try:
        with pytest.raises(NaipHTTPError) as error:
            naip_client.acquire(TEST_BBOX)
    finally:
        http_client.close()

    assert error.value.status_code == status_code
    assert str(status_code) in str(error.value)


def test_arcgis_http_error_message_is_preserved(tmp_path: Path) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/arcgis/rest/services/USGSNAIPPlus/ImageServer":
            return httpx.Response(200, json=service_payload(), request=request)
        return httpx.Response(
            400,
            json={"error": {"code": 400, "message": "Invalid bbox"}},
            request=request,
        )

    http_client = httpx.Client(transport=httpx.MockTransport(handler))
    naip_client = NaipClient(client=http_client, storage_directory=tmp_path)
    try:
        with pytest.raises(NaipHTTPError, match="Invalid bbox"):
            naip_client.acquire(TEST_BBOX)
    finally:
        http_client.close()


@pytest.mark.parametrize(
    ("failure", "expected_error"),
    [
        (httpx.ReadTimeout("timed out"), NaipTimeoutError),
        (httpx.ConnectError("connection failed"), NaipConnectionError),
    ],
)
def test_timeout_and_connection_errors_are_translated(
    tmp_path: Path,
    failure: BaseException,
    expected_error: type[Exception],
) -> None:
    naip_client, http_client, _ = client_for(tmp_path, image_failure=failure)
    try:
        with pytest.raises(expected_error):
            naip_client.acquire(TEST_BBOX)
    finally:
        http_client.close()


@pytest.mark.parametrize(
    ("content_type", "body"),
    [
        ("text/html", b"<html>service unavailable</html>"),
        ("application/json", b'{"error":{"message":"no data"}}'),
        ("image/tiff", b""),
    ],
)
def test_non_image_or_empty_responses_are_rejected(
    tmp_path: Path, content_type: str, body: bytes
) -> None:
    naip_client, http_client, _ = client_for(
        tmp_path,
        image_content_type=content_type,
        image_body_factory=lambda _: body,
    )
    try:
        with pytest.raises(NaipResponseError):
            naip_client.acquire(TEST_BBOX)
    finally:
        http_client.close()


def test_corrupted_tiff_is_rejected(tmp_path: Path) -> None:
    naip_client, http_client, _ = client_for(
        tmp_path,
        image_body_factory=lambda _: b"II*\x00this is not a TIFF",
    )
    try:
        with pytest.raises(NaipResponseError, match="readable GeoTIFF"):
            naip_client.acquire(TEST_BBOX)
    finally:
        http_client.close()


@pytest.mark.parametrize(
    ("raster_options", "message"),
    [
        ({"count": 3}, "Expected 4 raster bands"),
        ({"dtype": "float32"}, "Expected four uint8 bands"),
        ({"crs": "EPSG:4326"}, "Expected raster CRS EPSG:3857"),
    ],
)
def test_unsupported_raster_profiles_are_rejected(
    tmp_path: Path,
    raster_options: dict[str, object],
    message: str,
) -> None:
    def raster_body(request: httpx.Request) -> bytes:
        params = request.url.params
        width, height = (int(value) for value in params["size"].split(","))
        return tiny_geotiff(
            width,
            height,
            (0.0, 0.0, 100.0, 100.0),
            count=cast(int, raster_options.get("count", 4)),
            dtype=cast(str, raster_options.get("dtype", "uint8")),
            crs=cast(str, raster_options.get("crs", "EPSG:3857")),
        )

    naip_client, http_client, _ = client_for(tmp_path, image_body_factory=raster_body)
    try:
        with pytest.raises(NaipResponseError, match=message):
            naip_client.acquire(TEST_BBOX)
    finally:
        http_client.close()


def test_mismatched_dimensions_are_rejected(tmp_path: Path) -> None:
    def wrong_dimensions(request: httpx.Request) -> bytes:
        return tiny_geotiff(1, 1, (0.0, 0.0, 100.0, 100.0))

    naip_client, http_client, _ = client_for(tmp_path, image_body_factory=wrong_dimensions)
    try:
        with pytest.raises(NaipResponseError, match="dimensions different"):
            naip_client.acquire(TEST_BBOX)
    finally:
        http_client.close()


def test_raster_bounds_must_match_requested_projected_bbox(tmp_path: Path) -> None:
    def wrong_bounds(request: httpx.Request) -> bytes:
        params = request.url.params
        width, height = (int(value) for value in params["size"].split(","))
        return tiny_geotiff(width, height, (0.0, 0.0, 100.0, 100.0))

    naip_client, http_client, _ = client_for(tmp_path, image_body_factory=wrong_bounds)
    try:
        with pytest.raises(NaipResponseError, match="do not match the requested"):
            naip_client.acquire(TEST_BBOX)
    finally:
        http_client.close()


def test_fully_nodata_raster_is_rejected(tmp_path: Path) -> None:
    def no_data_body(request: httpx.Request) -> bytes:
        params = request.url.params
        width, height = (int(value) for value in params["size"].split(","))
        min_lon, min_lat, max_lon, max_lat = (
            float(value) for value in params["bbox"].split(",")
        )
        projected = transform_bounds(
            "EPSG:4326",
            "EPSG:3857",
            min_lon,
            min_lat,
            max_lon,
            max_lat,
            densify_pts=21,
        )
        return tiny_geotiff(
            width,
            height,
            projected,
            value=0,
            all_masked=True,
        )

    naip_client, http_client, _ = client_for(tmp_path, image_body_factory=no_data_body)
    try:
        with pytest.raises(NaipResponseError, match="no valid imagery pixels"):
            naip_client.acquire(TEST_BBOX)
    finally:
        http_client.close()


def test_invalid_service_metadata_and_malformed_json_are_rejected(tmp_path: Path) -> None:
    naip_client, http_client, _ = client_for(
        tmp_path,
        service_data={"name": "WrongService"},
    )
    try:
        with pytest.raises(NaipResponseError, match="did not identify USGSNAIPPlus"):
            naip_client.acquire(TEST_BBOX)
    finally:
        http_client.close()

    def malformed_metadata(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=b"not json", request=request)

    http_client = httpx.Client(transport=httpx.MockTransport(malformed_metadata))
    naip_client = NaipClient(client=http_client, storage_directory=tmp_path)
    try:
        with pytest.raises(NaipResponseError, match="not valid JSON"):
            naip_client.acquire(TEST_BBOX)
    finally:
        http_client.close()


def test_large_aoi_is_rejected_before_export_request(tmp_path: Path) -> None:
    naip_client, http_client, requests = client_for(
        tmp_path,
        target_resolution_web_mercator_meters_per_pixel=0.3,
        service_data=service_payload(max_image_width=10, max_image_height=10),
    )
    try:
        with pytest.raises(NaipAreaTooLargeError, match="Reduce the bbox"):
            naip_client.acquire(TEST_BBOX)
    finally:
        http_client.close()

    assert len(requests) == 1


def test_configured_response_byte_limit_is_enforced_before_export(tmp_path: Path) -> None:
    naip_client, http_client, requests = client_for(
        tmp_path,
        target_resolution_web_mercator_meters_per_pixel=5.0,
        max_response_bytes=32,
    )
    try:
        with pytest.raises(NaipAreaTooLargeError, match="response-byte limit"):
            naip_client.acquire(TEST_BBOX)
    finally:
        http_client.close()

    assert len(requests) == 1


def test_valid_wgs84_bbox_outside_web_mercator_latitude_fails_explicitly(
    tmp_path: Path,
) -> None:
    naip_client, http_client, requests = client_for(tmp_path)
    polar_bbox: dict[str, object] = {
        "min_lon": -10.0,
        "min_lat": 85.2,
        "max_lon": -9.9,
        "max_lat": 85.3,
    }
    try:
        with pytest.raises(NaipResponseError, match="EPSG:3857 Web Mercator range"):
            naip_client.acquire(polar_bbox)
    finally:
        http_client.close()

    assert len(requests) == 1


def test_project_default_storage_path_is_data_processed_imagery_naip() -> None:
    assert DEFAULT_STORAGE_DIRECTORY == (
        Path(__file__).resolve().parents[2] / "data" / "processed" / "imagery" / "naip"
    )
