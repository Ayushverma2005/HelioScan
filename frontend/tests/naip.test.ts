import assert from "node:assert/strict";
import test from "node:test";

import {
  buildNaipBboxFromCenter,
  isNaipAcquisitionResponse,
  requestNaipAcquisition,
  resolveNaipImageUrl,
} from "../lib/naip.ts";

test("buildNaipBboxFromCenter creates a WGS84 extent around a map point", () => {
  const bbox = buildNaipBboxFromCenter({ lat: 30.2672, lng: -97.7431 }, 0.01);

  assert.ok(Math.abs(bbox.min_lon - -97.7531) < 1e-10);
  assert.ok(Math.abs(bbox.min_lat - 30.2572) < 1e-10);
  assert.ok(Math.abs(bbox.max_lon - -97.7331) < 1e-10);
  assert.ok(Math.abs(bbox.max_lat - 30.2772) < 1e-10);
});

test("isNaipAcquisitionResponse accepts the backend acquisition contract", () => {
  const result = {
    acquisition_status: "acquired",
    acquisition_id: "naip_20260928T101112.123456Z",
    image_url: "/api/imagery/naip/naip_20260928T101112.123456Z/image",
    provider: "USGS",
    service_name: "USGSNAIPPlus",
    source_url: "https://imagery.nationalmap.gov/arcgis/rest/services/USGSNAIPPlus/ImageServer",
    attribution: "USGS, USDA, The National Map: Orthoimagery.",
    request_bbox: {
      min_lon: -97.829,
      min_lat: 30.487,
      max_lon: -97.8288,
      max_lat: 30.4872,
    },
    request_bbox_crs: "EPSG:4326",
    requested_size: [1024, 1024],
    requested_resolution_web_mercator_meters_per_pixel: 5,
    width: 1024,
    height: 1024,
    band_count: 4,
    dtype: "uint8",
    crs: "EPSG:3857",
    bounds: { left: 0, bottom: 0, right: 1, top: 1 },
    resolution: [1, 1],
    pixel_size: [1, 1],
    transform: [1, 0, 0, 1, 0, 0],
    format: "GTiff",
    pixel_type: "U8",
    band_ids: [1, 2, 3, 4],
    acquired_at: "2026-09-29T12:00:00Z",
    response_content_type: "image/tiff",
    response_headers: { "content-type": "image/tiff" },
    service_metadata: { provider: "USGS" },
  };

  assert.equal(isNaipAcquisitionResponse(result), true);
});

test("resolveNaipImageUrl keeps image retrieval on the same origin", () => {
  assert.equal(
    resolveNaipImageUrl("/api/imagery/naip/naip_20260928T101112.123456Z/image"),
    "/api/naip/image/naip_20260928T101112.123456Z",
  );
});

test("requestNaipAcquisition passes the WGS84 bbox to the backend and validates the response", async () => {
  const originalFetch = globalThis.fetch;

  try {
    globalThis.fetch = async (input: RequestInfo | URL, init?: RequestInit) => {
      assert.equal(String(input), "/api/naip");
      assert.equal(init?.method, "POST");
      const body = JSON.parse(String(init?.body ?? "{}"));
      assert.deepEqual(body, {
        min_lon: -97.83,
        min_lat: 30.48,
        max_lon: -97.82,
        max_lat: 30.49,
      });

      return new Response(
        JSON.stringify({
          acquisition_status: "acquired",
          acquisition_id: "naip_20260928T101112.123456Z",
          image_url: "/api/imagery/naip/naip_20260928T101112.123456Z/image",
          provider: "USGS",
          service_name: "USGSNAIPPlus",
          source_url: "https://imagery.nationalmap.gov/arcgis/rest/services/USGSNAIPPlus/ImageServer",
          attribution: "USGS, USDA, The National Map: Orthoimagery.",
          request_bbox: {
            min_lon: -97.83,
            min_lat: 30.48,
            max_lon: -97.82,
            max_lat: 30.49,
          },
          request_bbox_crs: "EPSG:4326",
          requested_size: [1024, 1024],
          requested_resolution_web_mercator_meters_per_pixel: 5,
          width: 1024,
          height: 1024,
          band_count: 4,
          dtype: "uint8",
          crs: "EPSG:3857",
          bounds: { left: 0, bottom: 0, right: 1, top: 1 },
          resolution: [1, 1],
          pixel_size: [1, 1],
          transform: [1, 0, 0, 1, 0, 0],
          format: "GTiff",
          pixel_type: "U8",
          band_ids: [1, 2, 3, 4],
          acquired_at: "2026-09-29T12:00:00Z",
          response_content_type: "image/tiff",
          response_headers: { "content-type": "image/tiff" },
          service_metadata: { provider: "USGS" },
        }),
        { status: 201, headers: { "Content-Type": "application/json" } },
      );
    };

    const result = await requestNaipAcquisition({
      min_lon: -97.83,
      min_lat: 30.48,
      max_lon: -97.82,
      max_lat: 30.49,
    });

    assert.equal(result.acquisition_status, "acquired");
    assert.equal(result.image_url, "/api/imagery/naip/naip_20260928T101112.123456Z/image");
  } finally {
    globalThis.fetch = originalFetch;
  }
});

test("requestNaipAcquisition maps backend HTTP error responses to a user-visible message", async () => {
  const originalFetch = globalThis.fetch;

  try {
    globalThis.fetch = async () =>
      new Response(
        JSON.stringify({
          detail: {
            code: "naip_provider_timeout",
            message: "The USGS NAIP Plus service did not respond in time.",
          },
        }),
        { status: 504, headers: { "Content-Type": "application/json" } },
      );

    await assert.rejects(requestNaipAcquisition({
      min_lon: -97.83,
      min_lat: 30.48,
      max_lon: -97.82,
      max_lat: 30.49,
    }), /in time/);
  } finally {
    globalThis.fetch = originalFetch;
  }
});

test("requestNaipAcquisition rejects a successful but malformed backend response", async () => {
  const originalFetch = globalThis.fetch;

  try {
    globalThis.fetch = async () => new Response(JSON.stringify({ acquisition_status: "acquired" }));

    await assert.rejects(
      requestNaipAcquisition({
        min_lon: -97.83,
        min_lat: 30.48,
        max_lon: -97.82,
        max_lat: 30.49,
      }),
      /Unexpected response/,
    );
  } finally {
    globalThis.fetch = originalFetch;
  }
});

