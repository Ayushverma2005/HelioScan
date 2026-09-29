"""Client for acquiring and validating USGS NAIP Plus imagery."""

from __future__ import annotations

import logging
import math
import os
import tempfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx
from rasterio.errors import RasterioError  # type: ignore[import-untyped]
from rasterio.io import MemoryFile  # type: ignore[import-untyped]
from rasterio.warp import transform_bounds  # type: ignore[import-untyped]

from app.imagery.errors import (
    NaipAreaTooLargeError,
    NaipConnectionError,
    NaipHTTPError,
    NaipResponseError,
    NaipTimeoutError,
)
from app.imagery.models import (
    AcquiredImagery,
    GeographicBBox,
    NaipImageMetadata,
    RasterBounds,
)

logger = logging.getLogger(__name__)

NAIP_IMAGE_SERVER_URL = (
    "https://imagery.nationalmap.gov/arcgis/rest/services/USGSNAIPPlus/ImageServer"
)
NAIP_EXPORT_IMAGE_URL = f"{NAIP_IMAGE_SERVER_URL}/exportImage"
NAIP_SERVICE_NAME = "USGSNAIPPlus"
NAIP_PROVIDER = "USGS"
NAIP_USER_AGENT = "HelioScan/0.1 (USGS NAIP Plus imagery client)"
WGS84_EPSG = 4326
WEB_MERCATOR_EPSG = 3857
MAX_WEB_MERCATOR_LATITUDE = 85.0511287798066
DEFAULT_TARGET_RESOLUTION_WEB_MERCATOR_METERS_PER_PIXEL = 0.3
DEFAULT_TIMEOUT_SECONDS = 30.0
DEFAULT_MAX_RESPONSE_BYTES = 128 * 1024 * 1024
EXPECTED_BAND_IDS = (0, 1, 2, 3)
TIFF_MEDIA_TYPES = {"image/tiff", "image/geotiff", "application/octet-stream"}
PROJECT_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_STORAGE_DIRECTORY = PROJECT_ROOT / "data" / "processed" / "imagery" / "naip"
PERSISTED_RESPONSE_HEADERS = ("content-type", "content-length", "etag", "last-modified")


@dataclass(frozen=True)
class _ServiceMetadata:
    copyright_text: str
    description: str
    max_image_width: int
    max_image_height: int
    spatial_reference: int
    band_count: int
    pixel_type: str
    capabilities: tuple[str, ...]
    mosaic_method: str | None
    mosaic_sort_field: str | None
    mosaic_sort_value: str | None
    mosaic_sort_ascending: bool | None
    mosaic_operator: str | None

    def as_dict(self) -> dict[str, object]:
        return {
            "name": NAIP_SERVICE_NAME,
            "description": self.description,
            "spatial_reference": self.spatial_reference,
            "pixel_type": self.pixel_type,
            "band_count": self.band_count,
            "capabilities": list(self.capabilities),
            "copyright_text": self.copyright_text,
            "max_image_width": self.max_image_width,
            "max_image_height": self.max_image_height,
            "default_mosaic_method": self.mosaic_method,
            "sort_field": self.mosaic_sort_field,
            "sort_value": self.mosaic_sort_value,
            "sort_ascending": self.mosaic_sort_ascending,
            "mosaic_operator": self.mosaic_operator,
        }


class NaipClient:
    """Acquire a bounded NAIP Plus GeoTIFF and persist its provenance metadata."""

    def __init__(
        self,
        client: httpx.Client | None = None,
        storage_directory: Path | None = None,
        timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
        target_resolution_web_mercator_meters_per_pixel: float = (
            DEFAULT_TARGET_RESOLUTION_WEB_MERCATOR_METERS_PER_PIXEL
        ),
        max_response_bytes: int = DEFAULT_MAX_RESPONSE_BYTES,
    ) -> None:
        if not math.isfinite(timeout_seconds) or timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be finite and greater than zero")
        if (
            not math.isfinite(target_resolution_web_mercator_meters_per_pixel)
            or target_resolution_web_mercator_meters_per_pixel <= 0
        ):
            raise ValueError(
                "target_resolution_web_mercator_meters_per_pixel must be finite "
                "and greater than zero"
            )
        if (
            isinstance(max_response_bytes, bool)
            or not isinstance(max_response_bytes, int)
            or max_response_bytes <= 0
        ):
            raise ValueError("max_response_bytes must be a positive integer")

        self._owns_client = client is None
        self._client = client or httpx.Client(
            headers={
                "User-Agent": NAIP_USER_AGENT,
                "Accept": "image/tiff, application/json",
            }
        )
        self._storage_directory = storage_directory or DEFAULT_STORAGE_DIRECTORY
        self._timeout = httpx.Timeout(timeout_seconds)
        self._target_resolution_web_mercator_meters_per_pixel = (
            target_resolution_web_mercator_meters_per_pixel
        )
        self._max_response_bytes = max_response_bytes

    def acquire(self, bbox: GeographicBBox | dict[str, object]) -> AcquiredImagery:
        """Fetch the supplied WGS84 bbox, validate the GeoTIFF, and persist it."""
        geographic_bbox = (
            bbox if isinstance(bbox, GeographicBBox) else GeographicBBox.model_validate(bbox)
        )
        service_metadata = self._get_service_metadata()
        projected_bounds = self._projected_bbox(geographic_bbox)
        width, height = self._requested_size(projected_bounds, service_metadata)
        request_params = self._export_parameters(geographic_bbox, width, height)
        image_bytes, response_headers = self._download_image(request_params)
        raster_properties = self._validate_raster(
            image_bytes,
            width,
            height,
            expected_bounds=projected_bounds,
        )
        acquired_at = datetime.now(timezone.utc)

        self._storage_directory.mkdir(parents=True, exist_ok=True)
        stamp = acquired_at.strftime("%Y%m%dT%H%M%S.%fZ")
        image_path = self._storage_directory / f"naip_{stamp}.tif"
        metadata_path = self._storage_directory / f"naip_{stamp}.json"
        metadata = NaipImageMetadata(
            provider=NAIP_PROVIDER,
            service_name=NAIP_SERVICE_NAME,
            service_url=NAIP_IMAGE_SERVER_URL,
            attribution=service_metadata.copyright_text,
            requested_bbox=geographic_bbox,
            requested_bbox_crs=f"EPSG:{WGS84_EPSG}",
            output_crs=f"EPSG:{WEB_MERCATOR_EPSG}",
            requested_size=(width, height),
            requested_resolution_web_mercator_meters_per_pixel=(
                self._target_resolution_web_mercator_meters_per_pixel
            ),
            width=raster_properties["width"],
            height=raster_properties["height"],
            band_count=raster_properties["band_count"],
            dtype=raster_properties["dtype"],
            raster_bounds=raster_properties["bounds"],
            resolution=raster_properties["resolution"],
            transform=raster_properties["transform"],
            requested_format="tiff",
            requested_pixel_type="U8",
            requested_band_ids=EXPECTED_BAND_IDS,
            acquired_at=acquired_at,
            storage_path=self._storage_path(image_path),
            response_content_type=response_headers.get("content-type"),
            response_headers=response_headers,
            service_metadata=service_metadata.as_dict(),
        )

        _atomic_write(image_path, image_bytes)
        try:
            _atomic_write(metadata_path, metadata.model_dump_json(indent=2).encode("utf-8"))
        except OSError:
            image_path.unlink(missing_ok=True)
            raise

        logger.info(
            "NAIP imagery acquired (service=%s, width=%d, height=%d, bands=%d)",
            NAIP_SERVICE_NAME,
            metadata.width,
            metadata.height,
            metadata.band_count,
        )
        return AcquiredImagery(
            image_path=image_path,
            metadata_path=metadata_path,
            metadata=metadata,
        )

    def close(self) -> None:
        """Close the HTTP client when this instance created it."""
        if self._owns_client:
            self._client.close()

    def __enter__(self) -> NaipClient:
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

    def _get_service_metadata(self) -> _ServiceMetadata:
        response = self._get(
            NAIP_IMAGE_SERVER_URL,
            params={"f": "json"},
        )
        try:
            payload = response.json()
        except ValueError as exc:
            raise NaipResponseError("ImageServer metadata response was not valid JSON") from exc
        if not isinstance(payload, dict):
            raise NaipResponseError("ImageServer metadata response must be a JSON object")
        return _parse_service_metadata(payload)

    def _get(self, url: str, *, params: dict[str, str | int]) -> httpx.Response:
        try:
            response = self._client.get(url, params=params, timeout=self._timeout)
        except httpx.TimeoutException as exc:
            raise NaipTimeoutError("USGS NAIP Plus request timed out") from exc
        except httpx.RequestError as exc:
            raise NaipConnectionError("Could not connect to USGS NAIP Plus ImageServer") from exc
        _raise_for_http_error(response)
        return response

    def _download_image(
        self, params: dict[str, str | int]
    ) -> tuple[bytes, dict[str, str]]:
        try:
            with self._client.stream(
                "GET",
                NAIP_EXPORT_IMAGE_URL,
                params=params,
                timeout=self._timeout,
            ) as response:
                _raise_for_http_error(response)
                content_type = response.headers.get("content-type")
                _validate_content_type(content_type)
                content_length = response.headers.get("content-length")
                if content_length is not None:
                    try:
                        if int(content_length) > self._max_response_bytes:
                            raise NaipAreaTooLargeError(
                                "NAIP response exceeds the configured byte limit"
                            )
                    except ValueError as exc:
                        raise NaipResponseError(
                            "NAIP response has an invalid Content-Length"
                        ) from exc

                chunks = bytearray()
                for chunk in response.iter_bytes():
                    if len(chunks) + len(chunk) > self._max_response_bytes:
                        raise NaipAreaTooLargeError(
                            "NAIP response exceeds the configured byte limit"
                        )
                    chunks.extend(chunk)
                headers = {
                    name: response.headers[name]
                    for name in PERSISTED_RESPONSE_HEADERS
                    if name in response.headers
                }
        except httpx.TimeoutException as exc:
            raise NaipTimeoutError("USGS NAIP Plus image request timed out") from exc
        except httpx.RequestError as exc:
            raise NaipConnectionError("Could not download from USGS NAIP Plus ImageServer") from exc

        image_bytes = bytes(chunks)
        if not image_bytes:
            raise NaipResponseError("USGS NAIP Plus returned an empty image body")
        if not _has_tiff_signature(image_bytes):
            raise NaipResponseError("USGS NAIP Plus response is not a TIFF image")
        return image_bytes, headers

    def _projected_bbox(self, bbox: GeographicBBox) -> tuple[float, float, float, float]:
        if (
            bbox.min_lat < -MAX_WEB_MERCATOR_LATITUDE
            or bbox.max_lat > MAX_WEB_MERCATOR_LATITUDE
        ):
            raise NaipResponseError(
                "bbox latitude exceeds the supported EPSG:3857 Web Mercator range"
            )
        try:
            projected_bounds = transform_bounds(
                f"EPSG:{WGS84_EPSG}",
                f"EPSG:{WEB_MERCATOR_EPSG}",
                bbox.min_lon,
                bbox.min_lat,
                bbox.max_lon,
                bbox.max_lat,
                densify_pts=21,
            )
            bounds = tuple(float(value) for value in projected_bounds)
        except (ValueError, RasterioError) as exc:
            raise NaipResponseError("Could not project WGS84 bbox to EPSG:3857") from exc
        if len(bounds) != 4:
            raise NaipResponseError("Projected bbox did not produce four bounds")
        if not all(math.isfinite(value) for value in bounds):
            raise NaipResponseError("Projected bbox contains non-finite coordinates")
        if bounds[0] >= bounds[2] or bounds[1] >= bounds[3]:
            raise NaipResponseError("Projected bbox has invalid bounds")
        return (bounds[0], bounds[1], bounds[2], bounds[3])

    def _requested_size(
        self,
        projected_bounds: tuple[float, float, float, float],
        service: _ServiceMetadata,
    ) -> tuple[int, int]:
        min_x, min_y, max_x, max_y = projected_bounds
        width = math.ceil(
            (max_x - min_x) / self._target_resolution_web_mercator_meters_per_pixel
        )
        height = math.ceil(
            (max_y - min_y) / self._target_resolution_web_mercator_meters_per_pixel
        )
        if width > service.max_image_width or height > service.max_image_height:
            raise NaipAreaTooLargeError(
                "Requested bbox requires an export of "
                f"{width}x{height} pixels at "
                f"{self._target_resolution_web_mercator_meters_per_pixel:g} "
                "EPSG:3857 map meters/pixel; "
                f"the service limit is {service.max_image_width}x{service.max_image_height}. "
                "Reduce the bbox or explicitly request a coarser target resolution."
            )
        expected_bytes = width * height * service.band_count
        if expected_bytes > self._max_response_bytes:
            raise NaipAreaTooLargeError(
                "Requested NAIP raster exceeds the configured response-byte limit"
            )
        return width, height

    @staticmethod
    def _export_parameters(
        bbox: GeographicBBox, width: int, height: int
    ) -> dict[str, str | int]:
        bbox_text = ",".join(
            format(value, ".15g")
            for value in (bbox.min_lon, bbox.min_lat, bbox.max_lon, bbox.max_lat)
        )
        return {
            "bbox": bbox_text,
            "bboxSR": WGS84_EPSG,
            "imageSR": WEB_MERCATOR_EPSG,
            "size": f"{width},{height}",
            "format": "tiff",
            "pixelType": "U8",
            "bandIds": ",".join(str(band_id) for band_id in EXPECTED_BAND_IDS),
            "interpolation": "RSP_BilinearInterpolation",
            "compression": "LZ77",
            "adjustAspectRatio": "false",
            "f": "image",
        }

    @staticmethod
    def _validate_raster(
        image_bytes: bytes,
        expected_width: int,
        expected_height: int,
        *,
        expected_bounds: tuple[float, float, float, float],
    ) -> dict[str, Any]:
        try:
            with MemoryFile(image_bytes) as memory_file:
                with memory_file.open() as dataset:
                    if dataset.driver != "GTiff":
                        raise NaipResponseError(
                            f"Expected a GeoTIFF response, got raster driver {dataset.driver!r}"
                        )
                    if dataset.width != expected_width or dataset.height != expected_height:
                        raise NaipResponseError(
                            "ImageServer returned dimensions different from the explicitly "
                            f"requested {expected_width}x{expected_height} pixels"
                        )
                    if dataset.count != len(EXPECTED_BAND_IDS):
                        raise NaipResponseError(
                            "Expected 4 raster bands, "
                            f"received {dataset.count}"
                        )
                    if dataset.dtypes != ("uint8",) * len(EXPECTED_BAND_IDS):
                        raise NaipResponseError(
                            f"Expected four uint8 bands, received {dataset.dtypes}"
                        )
                    if dataset.crs is None or dataset.crs.to_epsg() != WEB_MERCATOR_EPSG:
                        raise NaipResponseError(
                            "Expected raster CRS EPSG:3857, "
                            f"received {dataset.crs!s}"
                        )
                    if dataset.transform.is_identity:
                        raise NaipResponseError("Raster has no georeferencing transform")

                    transform = tuple(float(value) for value in dataset.transform[:6])
                    bounds = (
                        float(dataset.bounds.left),
                        float(dataset.bounds.bottom),
                        float(dataset.bounds.right),
                        float(dataset.bounds.top),
                    )
                    resolution = (float(dataset.res[0]), float(dataset.res[1]))
                    georeferencing = (*transform, *bounds, *resolution)
                    if not all(math.isfinite(value) for value in georeferencing):
                        raise NaipResponseError("Raster georeferencing contains non-finite values")
                    if bounds[0] >= bounds[2] or bounds[1] >= bounds[3]:
                        raise NaipResponseError("Raster has invalid georeferenced bounds")
                    if resolution[0] <= 0 or resolution[1] <= 0:
                        raise NaipResponseError("Raster has invalid pixel resolution")
                    if abs(transform[0] * transform[4] - transform[1] * transform[3]) == 0:
                        raise NaipResponseError("Raster transform is singular")
                    bounds_tolerance = max(resolution)
                    if any(
                        abs(actual - expected) > bounds_tolerance
                        for actual, expected in zip(bounds, expected_bounds, strict=True)
                    ):
                        raise NaipResponseError(
                            "Raster bounds do not match the requested projected bbox"
                        )
                    if not dataset.dataset_mask().any():
                        raise NaipResponseError("Raster contains no valid imagery pixels")

                    return {
                        "width": dataset.width,
                        "height": dataset.height,
                        "band_count": dataset.count,
                        "dtype": dataset.dtypes[0],
                        "bounds": RasterBounds(
                            left=bounds[0],
                            bottom=bounds[1],
                            right=bounds[2],
                            top=bounds[3],
                        ),
                        "resolution": resolution,
                        "transform": transform,
                    }
        except NaipResponseError:
            raise
        except (RasterioError, ValueError, OSError) as exc:
            raise NaipResponseError("USGS NAIP Plus response is not a readable GeoTIFF") from exc

    @staticmethod
    def _storage_path(path: Path) -> str:
        try:
            return path.resolve().relative_to(PROJECT_ROOT).as_posix()
        except ValueError:
            return path.resolve().as_posix()


def _parse_service_metadata(payload: dict[str, Any]) -> _ServiceMetadata:
    if payload.get("name") != NAIP_SERVICE_NAME:
        raise NaipResponseError("ImageServer metadata did not identify USGSNAIPPlus")

    spatial_reference = payload.get("spatialReference")
    if not isinstance(spatial_reference, dict):
        raise NaipResponseError("ImageServer metadata omitted its spatial reference")
    wkid: object = spatial_reference.get("latestWkid", spatial_reference.get("wkid"))
    if isinstance(wkid, bool) or not isinstance(wkid, (int, str)):
        raise NaipResponseError("ImageServer metadata has an invalid spatial reference")
    try:
        spatial_reference_wkid = int(wkid)
    except (TypeError, ValueError) as exc:
        raise NaipResponseError("ImageServer metadata has an invalid spatial reference") from exc
    if spatial_reference_wkid not in {WEB_MERCATOR_EPSG, 102100}:
        raise NaipResponseError(
            f"ImageServer metadata advertised unsupported WKID {spatial_reference_wkid}"
        )

    try:
        band_count = int(payload["bandCount"])
        max_image_width = int(payload["maxImageWidth"])
        max_image_height = int(payload["maxImageHeight"])
    except (KeyError, TypeError, ValueError) as exc:
        raise NaipResponseError("ImageServer metadata omitted required raster limits") from exc

    capabilities_value = payload.get("capabilities")
    if not isinstance(capabilities_value, str):
        raise NaipResponseError("ImageServer metadata omitted its capabilities")
    capabilities = tuple(value.strip() for value in capabilities_value.split(","))
    if "Image" not in capabilities:
        raise NaipResponseError("USGSNAIPPlus ImageServer does not advertise Image capability")

    pixel_type = payload.get("pixelType")
    copyright_text = payload.get("copyrightText")
    if pixel_type != "U8" or band_count != len(EXPECTED_BAND_IDS):
        raise NaipResponseError(
            "USGSNAIPPlus raster profile changed; expected 4-band U8 imagery"
        )
    if not isinstance(copyright_text, str) or not copyright_text.strip():
        raise NaipResponseError("ImageServer metadata omitted source attribution")
    if max_image_width <= 0 or max_image_height <= 0:
        raise NaipResponseError("ImageServer metadata advertised invalid image dimensions")

    sort_ascending_value = payload.get("sortAscending")
    return _ServiceMetadata(
        copyright_text=copyright_text.strip(),
        description=str(payload.get("serviceDescription", "")),
        max_image_width=max_image_width,
        max_image_height=max_image_height,
        spatial_reference=spatial_reference_wkid,
        band_count=band_count,
        pixel_type=pixel_type,
        capabilities=capabilities,
        mosaic_method=_optional_text(payload.get("defaultMosaicMethod")),
        mosaic_sort_field=_optional_text(payload.get("sortField")),
        mosaic_sort_value=_optional_text(payload.get("sortValue")),
        mosaic_sort_ascending=(
            sort_ascending_value if isinstance(sort_ascending_value, bool) else None
        ),
        mosaic_operator=_optional_text(payload.get("mosaicOperator")),
    )


def _optional_text(value: object) -> str | None:
    return value if isinstance(value, str) else None


def _raise_for_http_error(response: httpx.Response) -> None:
    if not response.is_error:
        return
    detail = _http_error_detail(response)
    raise NaipHTTPError(response.status_code, detail)


def _http_error_detail(response: httpx.Response) -> str | None:
    content_type = response.headers.get("content-type", "").lower()
    if "json" not in content_type:
        return None
    try:
        payload = response.json()
    except ValueError:
        return None
    if not isinstance(payload, dict):
        return None
    error = payload.get("error")
    if not isinstance(error, dict):
        return None
    message = error.get("message")
    if isinstance(message, str):
        return message[:300]
    return None


def _validate_content_type(content_type: str | None) -> None:
    if content_type is None:
        return
    media_type = content_type.split(";", maxsplit=1)[0].strip().lower()
    if media_type not in TIFF_MEDIA_TYPES:
        raise NaipResponseError(
            "USGS NAIP Plus returned a non-TIFF content type "
            f"({media_type or 'empty'})"
        )


def _has_tiff_signature(image_bytes: bytes) -> bool:
    return image_bytes[:4] in {
        b"II*\x00",
        b"MM\x00*",
        b"II+\x00",
        b"MM\x00+",
    }


def _atomic_write(path: Path, content: bytes) -> None:
    file_descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.",
        suffix=".tmp",
        dir=path.parent,
    )
    temporary_path = Path(temporary_name)
    try:
        with os.fdopen(file_descriptor, "wb") as temporary_file:
            temporary_file.write(content)
            temporary_file.flush()
            os.fsync(temporary_file.fileno())
        os.replace(temporary_path, path)
    finally:
        temporary_path.unlink(missing_ok=True)