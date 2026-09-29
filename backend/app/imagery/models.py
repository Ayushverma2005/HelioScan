"""Validated geographic requests and NAIP acquisition metadata."""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class GeographicBBox(BaseModel):
    """A non-wrapping WGS84 geographic bounding box in decimal degrees."""

    model_config = ConfigDict(extra="forbid")

    min_lon: float = Field(ge=-180.0, le=180.0)
    min_lat: float = Field(ge=-90.0, le=90.0)
    max_lon: float = Field(ge=-180.0, le=180.0)
    max_lat: float = Field(ge=-90.0, le=90.0)

    @field_validator("min_lon", "min_lat", "max_lon", "max_lat", mode="before")
    @classmethod
    def require_finite_numeric_coordinate(cls, value: object) -> float:
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ValueError("bbox coordinates must be numeric values")
        coordinate = float(value)
        if not math.isfinite(coordinate):
            raise ValueError("bbox coordinates must be finite")
        return coordinate

    @model_validator(mode="after")
    def require_increasing_bounds(self) -> GeographicBBox:
        if self.min_lon >= self.max_lon:
            raise ValueError("min_lon must be less than max_lon")
        if self.min_lat >= self.max_lat:
            raise ValueError("min_lat must be less than max_lat")
        return self


class RasterBounds(BaseModel):
    """Raster bounds in the output raster's coordinate reference system."""

    model_config = ConfigDict(extra="forbid")

    left: float
    bottom: float
    right: float
    top: float


class NaipImageMetadata(BaseModel):
    """Persisted provenance and raster properties for an acquired NAIP image."""

    model_config = ConfigDict(extra="forbid")

    provider: str
    service_name: str
    service_url: str
    attribution: str
    requested_bbox: GeographicBBox
    requested_bbox_crs: str
    output_crs: str
    requested_size: tuple[int, int]
    requested_resolution_web_mercator_meters_per_pixel: float
    width: int
    height: int
    band_count: int
    dtype: str
    raster_bounds: RasterBounds
    resolution: tuple[float, float]
    transform: tuple[float, float, float, float, float, float]
    requested_format: str
    requested_pixel_type: str
    requested_band_ids: tuple[int, ...]
    acquired_at: datetime
    storage_path: str
    response_content_type: str | None
    response_headers: dict[str, str]
    service_metadata: dict[str, object]


@dataclass(frozen=True)
class AcquiredImagery:
    """Paths and metadata returned by a successful NAIP acquisition."""

    image_path: Path
    metadata_path: Path
    metadata: NaipImageMetadata