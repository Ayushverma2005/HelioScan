"""Optional live smoke check for a small Cedar Park, Texas NAIP AOI."""

from __future__ import annotations

from app.imagery.client import NaipClient
from app.imagery.models import GeographicBBox

CEDAR_PARK_TEST_BBOX = GeographicBBox(
    min_lon=-97.8290,
    min_lat=30.4870,
    max_lon=-97.8288,
    max_lat=30.4872,
)


def main() -> int:
    """Acquire one small AOI, reopen it, and print the validated raster facts."""
    import rasterio  # type: ignore[import-untyped]

    with NaipClient() as client:
        acquisition = client.acquire(CEDAR_PARK_TEST_BBOX)

    with rasterio.open(acquisition.image_path) as dataset:
        if dataset.count != 4 or dataset.dtypes != ("uint8",) * 4:
            raise RuntimeError("Live NAIP raster did not validate as four uint8 bands")
        if dataset.crs is None or dataset.crs.to_epsg() != 3857:
            raise RuntimeError("Live NAIP raster did not validate as EPSG:3857")

        print(f"Image: {acquisition.image_path}")
        print(f"Metadata: {acquisition.metadata_path}")
        print(f"Dimensions: {dataset.width} x {dataset.height}")
        print(f"Bands: {dataset.count}")
        print(f"Dtypes: {dataset.dtypes}")
        print(f"CRS: {dataset.crs}")
        print(f"Bounds: {dataset.bounds}")
        print(f"Resolution: {dataset.res}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())