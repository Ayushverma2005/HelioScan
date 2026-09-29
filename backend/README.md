# backend/

FastAPI application and provider/service modules for HelioScan. Current implemented slices include health, geocoding, and the Phase 5 NAIP acquisition client.

## NAIP acquisition

`app.imagery.NaipClient` accepts a WGS84 `GeographicBBox`, requests an explicitly sized four-band U8 GeoTIFF from the USGS NAIP Plus ImageServer in EPSG:3857, validates the raster with Rasterio, and persists the TIFF with a JSON metadata sidecar under `data/processed/imagery/naip/` by default.

Run the mocked backend tests from this directory:

```bash
python -m pytest
```

An optional live smoke check for a small Cedar Park, Texas AOI can be run from this directory with:

```bash
python -m app.imagery.live_check
```

The live check requires network access and is not part of the default test suite. Do not distribute acquired imagery unless current source terms permit it. See [`../docs/PHASE_05_NAIP_VERIFICATION.md`](../docs/PHASE_05_NAIP_VERIFICATION.md).
