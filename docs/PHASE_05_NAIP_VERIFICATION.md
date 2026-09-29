# Phase 5 - NAIP Plus Imagery Verification

**Checked:** 2026-09-28  
**Scope:** USGS NAIP Plus ImageServer metadata and ArcGIS REST export request behavior for the Phase 5 acquisition client. This does not certify global coverage, legal redistribution rights, or production availability guarantees.

## Selected source and scope

HelioScan imagery scope is US-focused. The selected service is the USGS NAIP Plus ImageServer:

- Service: https://imagery.nationalmap.gov/arcgis/rest/services/USGSNAIPPlus/ImageServer
- Export operation: `https://imagery.nationalmap.gov/arcgis/rest/services/USGSNAIPPlus/ImageServer/exportImage`
- Service metadata resource: append `?f=json` to the ImageServer URL.

The official service description says USGS NAIP Plus combines NAIP and high-resolution orthoimagery and that resolution varies by location. The service's full spatial extent is not a guarantee of NAIP coverage for every location. This implementation is intended only for US AOIs. It does not provide India or worldwide imagery coverage and does not fall back to another provider.

## Observed service metadata

The official service metadata was queried on 2026-09-28 and reported:

- Service name: `USGSNAIPPlus`
- Spatial reference: WKID 102100, latest WKID 3857 (Web Mercator)
- Pixel type: `U8`
- Band count: 4
- Capabilities: Image, Metadata, Catalog, Mensuration
- Maximum export dimensions: 4000 by 4000 pixels
- Attribution text: `USGS, USDA, The National Map: Orthoimagery. March 12, 2025.`
- Raster functions include natural color and false-color composites; the acquisition client requests all four service bands explicitly and does not apply a rendering rule.

The service metadata is checked at acquisition time for its name, projection, band profile, image capability, attribution, and dimension limits. A changed/incompatible profile fails explicitly rather than silently changing output assumptions.

## Request contract

Input bbox coordinates are WGS84 decimal degrees in `min_lon,min_lat,max_lon,max_lat` order. The client projects the extent to EPSG:3857 for output-size calculation and explicitly requests:

- `bboxSR=4326`
- `imageSR=3857`
- `size=<width>,<height>` computed from projected extent and configured target resolution, without aspect-ratio adjustment
- `format=tiff`, `pixelType=U8`, `bandIds=0,1,2,3`
- `interpolation=RSP_BilinearInterpolation`, `compression=LZ77`
- `f=image` for directly streamed image bytes

The REST parameter meanings and response modes were checked against the [official ArcGIS ImageServer Export Image reference](https://developers.arcgis.com/rest/services-reference/enterprise/export-image/). The service endpoint and profile were checked from the official USGS service metadata above. The client does not rely on default bbox CRS, output CRS, size, format, selected bands, resampling, compression, or response type.

The configured pixel spacing is in EPSG:3857 projected map meters per pixel. Web Mercator map units are not a ground-sample-distance claim; no GSD is inferred from the export size.

## Validation and storage

The client streams the response with a finite timeout and configured byte cap. It rejects HTTP errors, non-TIFF content types when supplied, empty bodies, non-TIFF signatures, unreadable rasters, mismatched requested dimensions, non-four-band/non-U8 outputs, missing/non-EPSG:3857 CRS, and invalid geotransforms/bounds/resolution.

Rasterio is pinned as `rasterio==1.5.1` in `backend/requirements.txt`. This was not an arbitrary version choice: Rasterio 1.5.1 was already installed in the project's ML environment and successfully read the existing four-band Cedar Park fixture; its installed package metadata requires Python `>=3.12`, and the backend venv is Python 3.12.3. The backend venv lacked Rasterio, so the same tested version is declared for the acquisition service.

Successful images are written under `data/processed/imagery/naip/` by default, with a JSON sidecar containing the request bbox/CRS, output CRS, dimensions, bands, dtype, raster bounds, resolution, transform, requested export options, acquisition timestamp, response headers, service metadata, and source attribution. Writes are atomic. Large imagery is local generated data and must not be committed to Git.

Requests exceeding the observed single-export dimensions or configured response-byte cap fail with an actionable size error. The client does not silently rescale a large extent or couple imagery acquisition to Model M's later 512x512 inference tiles.

## Validation evidence and open terms

The project owner previously reported a successful live Cedar Park export and Rasterio inspection: HTTP 200, 4-band GeoTIFF, EPSG:3857, and local persistence. This is retained as prior validation evidence; the normal unit tests use only mocked HTTP and tiny in-memory rasters.

An optional small-AOI checker is available as `python -m app.imagery.live_check` from `backend/`. It has not been run as part of the mocked test suite and does not invoke Model M.

The service metadata provides attribution text and exposes `allowCopy`, but these facts alone are not a legal determination of terms for every use or redistribution. Review current official USGS/The National Map and USDA/FSA terms for the intended storage, presentation, caching, and redistribution before shipping imagery through HelioScan. Do not claim ownership of imagery. The service itself states that NAIP and high-resolution orthoimagery coverage/resolution vary by location.