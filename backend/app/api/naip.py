"""FastAPI routes for USGS NAIP Plus acquisition and image retrieval."""

import re
from collections.abc import Generator
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse, Response
from pydantic import BaseModel, ConfigDict

from app.imagery.preview import create_naip_preview

from app.imagery import (
    AcquiredImagery,
    GeographicBBox,
    NaipAreaTooLargeError,
    NaipClient,
    NaipConnectionError,
    NaipHTTPError,
    NaipImageryError,
    NaipResponseError,
    NaipTimeoutError,
)
from app.imagery.client import DEFAULT_STORAGE_DIRECTORY
from app.imagery.models import RasterBounds

router = APIRouter(prefix="/api")
ACQUISITION_ID_PATTERN = re.compile(r"naip_[0-9]{8}T[0-9]{6}\.[0-9]{6}Z")


class NaipAcquisitionRequest(GeographicBBox):
    """US-only NAIP acquisition request using WGS84 longitude/latitude bounds."""


class NaipAcquisitionResponse(BaseModel):
    """Acquisition result and safe same-origin reference to the stored raster."""

    model_config = ConfigDict(extra="forbid")

    acquisition_status: Literal["acquired"]
    acquisition_id: str
    image_url: str
    provider: str
    service_name: str
    source_url: str
    attribution: str
    request_bbox: GeographicBBox
    request_bbox_crs: str
    requested_size: tuple[int, int]
    requested_resolution_web_mercator_meters_per_pixel: float
    width: int
    height: int
    band_count: int
    dtype: str
    crs: str
    bounds: RasterBounds
    resolution: tuple[float, float]
    pixel_size: tuple[float, float]
    transform: tuple[float, float, float, float, float, float]
    format: str
    pixel_type: str
    band_ids: tuple[int, ...]
    acquired_at: str
    response_content_type: str | None
    response_headers: dict[str, str]
    service_metadata: dict[str, object]


def get_naip_client() -> Generator[NaipClient, None, None]:
    """Create a client for one request and close its HTTP session afterward."""
    client = NaipClient()
    try:
        yield client
    finally:
        client.close()


@router.post(
    "/imagery/naip",
    response_model=NaipAcquisitionResponse,
    status_code=201,
)
def acquire_naip(
    request: NaipAcquisitionRequest,
    client: Annotated[NaipClient, Depends(get_naip_client)],
) -> NaipAcquisitionResponse:
    """Acquire validated USGS NAIP Plus imagery for a WGS84 bounding box."""
    try:
        acquisition = client.acquire(request)
    except NaipAreaTooLargeError as exc:
        raise _acquisition_exception(
            status_code=413,
            code="naip_aoi_too_large",
            message=str(exc),
        ) from exc
    except NaipHTTPError as exc:
        raise _acquisition_exception(
            status_code=502,
            code="naip_provider_http_error",
            message="The USGS NAIP Plus service returned an HTTP error.",
        ) from exc
    except NaipTimeoutError as exc:
        raise _acquisition_exception(
            status_code=504,
            code="naip_provider_timeout",
            message="The USGS NAIP Plus service did not respond in time.",
        ) from exc
    except NaipConnectionError as exc:
        raise _acquisition_exception(
            status_code=503,
            code="naip_provider_unavailable",
            message="The USGS NAIP Plus service is unavailable.",
        ) from exc
    except NaipResponseError as exc:
        raise _acquisition_exception(
            status_code=502,
            code="naip_provider_invalid_response",
            message="The USGS NAIP Plus service returned invalid imagery or metadata.",
        ) from exc
    except NaipImageryError as exc:
        raise _acquisition_exception(
            status_code=502,
            code="naip_acquisition_failed",
            message="NAIP imagery acquisition failed.",
        ) from exc

    return _to_response(acquisition)


@router.get("/imagery/naip/{acquisition_id}/image", response_class=FileResponse)
def get_naip_image(acquisition_id: str) -> FileResponse:
    """Serve an acquired TIFF by its opaque generated identifier, never by path."""
    if ACQUISITION_ID_PATTERN.fullmatch(acquisition_id) is None:
        raise HTTPException(status_code=404, detail="NAIP acquisition not found")

    storage_directory = DEFAULT_STORAGE_DIRECTORY.resolve()
    image_path = (storage_directory / f"{acquisition_id}.tif").resolve()
    if image_path.parent != storage_directory or not image_path.is_file():
        raise HTTPException(status_code=404, detail="NAIP acquisition not found")

    return FileResponse(
        image_path,
        media_type="image/tiff",
        headers={"Content-Disposition": f'inline; filename="{acquisition_id}.tif"'},
    )


def _to_response(acquisition: AcquiredImagery) -> NaipAcquisitionResponse:
    metadata = acquisition.metadata
    acquisition_id = acquisition.image_path.stem
    return NaipAcquisitionResponse(
        acquisition_status="acquired",
        acquisition_id=acquisition_id,
        image_url=f"/api/imagery/naip/{acquisition_id}/image",
        provider=metadata.provider,
        service_name=metadata.service_name,
        source_url=metadata.service_url,
        attribution=metadata.attribution,
        request_bbox=metadata.requested_bbox,
        request_bbox_crs=metadata.requested_bbox_crs,
        requested_size=metadata.requested_size,
        requested_resolution_web_mercator_meters_per_pixel=(
            metadata.requested_resolution_web_mercator_meters_per_pixel
        ),
        width=metadata.width,
        height=metadata.height,
        band_count=metadata.band_count,
        dtype=metadata.dtype,
        crs=metadata.output_crs,
        bounds=metadata.raster_bounds,
        resolution=metadata.resolution,
        pixel_size=metadata.resolution,
        transform=metadata.transform,
        format=metadata.requested_format,
        pixel_type=metadata.requested_pixel_type,
        band_ids=metadata.requested_band_ids,
        acquired_at=metadata.acquired_at.isoformat(),
        response_content_type=metadata.response_content_type,
        response_headers=metadata.response_headers,
        service_metadata=metadata.service_metadata,
    )


def _acquisition_exception(status_code: int, code: str, message: str) -> HTTPException:
    return HTTPException(status_code=status_code, detail={"code": code, "message": message})


@router.get(
    "/naip/{acquisition_id}/preview",
    summary="Preview NAIP imagery",
)
def preview_naip(acquisition_id: str):
    """Generate a browser-friendly PNG preview from an acquired NAIP TIFF."""
    if ACQUISITION_ID_PATTERN.fullmatch(acquisition_id) is None:
        raise HTTPException(
            status_code=404,
            detail="NAIP imagery not found",
        )

    storage_directory = DEFAULT_STORAGE_DIRECTORY.resolve()
    tiff_path = (storage_directory / f"{acquisition_id}.tif").resolve()

    if tiff_path.parent != storage_directory or not tiff_path.is_file():
        raise HTTPException(
            status_code=404,
            detail="NAIP imagery not found",
        )

    try:
        preview = create_naip_preview(tiff_path)

    except FileNotFoundError:
        raise HTTPException(
            status_code=404,
            detail="NAIP imagery not found",
        )

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Unable to generate NAIP preview: {exc}",
        )

    return Response(
        content=preview.getvalue(),
        media_type="image/png",
        headers={
            "Content-Disposition": (
                f'inline; filename="{acquisition_id}_preview.png"'
            )
        },
    )