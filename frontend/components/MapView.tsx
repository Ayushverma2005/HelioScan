"use client";

import { useEffect, useEffectEvent, useMemo } from "react";
import parseGeoraster from "georaster";
import GeoRasterLayer from "georaster-layer-for-leaflet";
import { MapContainer, Marker, Popup, TileLayer, useMap } from "react-leaflet";
import L from "leaflet";
import type { GeocodingResult } from "@/lib/geocode";
import "leaflet/dist/leaflet.css";

const PLACE_ZOOM = 12;
const OSM_TILE_URL = "https://tile.openstreetmap.org/{z}/{x}/{y}.png";

type NaipMapImage = {
  url: string;
  attribution: string;
};

function isValidLatitude(value: number): boolean {
  return Number.isFinite(value) && value >= -90 && value <= 90;
}

function isValidLongitude(value: number): boolean {
  return Number.isFinite(value) && value >= -180 && value <= 180;
}

function MapCenter({ selected }: { selected: GeocodingResult | null }) {
  const map = useMap();

  useEffect(() => {
    if (!selected) {
      return;
    }

    const latitude = Number(selected.latitude);
    const longitude = Number(selected.longitude);
    if (!isValidLatitude(latitude) || !isValidLongitude(longitude)) {
      return;
    }

    map.setView([latitude, longitude], PLACE_ZOOM, { animate: true, duration: 0.5 });
  }, [map, selected]);

  return null;
}

function NaipRasterOverlay({
  image,
  onError,
}: {
  image: NaipMapImage;
  onError: (message: string) => void;
}) {
  const map = useMap();
  const reportError = useEffectEvent(onError);

  useEffect(() => {
    let cancelled = false;
    let rasterLayer: L.Layer | null = null;

    async function loadRaster() {
      try {
        const response = await fetch(image.url, { cache: "no-store" });
        if (!response.ok) {
          throw new Error("NAIP image request failed.");
        }

        const georaster = await parseGeoraster(await response.arrayBuffer());
        if (cancelled) {
          return;
        }

        const layer = new GeoRasterLayer({
          georaster,
          opacity: 0.9,
          attribution: image.attribution,
          resolution: 256,
          pixelValuesToColorFn: (values) => {
            if (
              values.length < 3 ||
              values.every((value) => value === georaster.noDataValue) ||
              values[3] === 0
            ) {
              return null;
            }

            return `rgb(${values[0]}, ${values[1]}, ${values[2]})`;
          },
        });
        rasterLayer = layer;
        layer.addTo(map);
      } catch {
        if (!cancelled) {
          reportError("The acquired NAIP image could not be loaded on the map.");
        }
      }
    }

    void loadRaster();

    return () => {
      cancelled = true;
      if (rasterLayer) {
        map.removeLayer(rasterLayer);
      }
    };
  }, [image.attribution, image.url, map]);

  return null;
}

export default function MapView({
  selected,
  naipImage,
  onNaipError,
}: {
  selected: GeocodingResult | null;
  naipImage: NaipMapImage | null;
  onNaipError: (message: string) => void;
}) {
  const validSelection =
    selected !== null &&
    isValidLatitude(Number(selected.latitude)) &&
    isValidLongitude(Number(selected.longitude));

  const markerIcon = useMemo(() => {
    if (typeof window === "undefined") {
      return undefined;
    }

    return L.icon({
      iconUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png",
      iconRetinaUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon-2x.png",
      shadowUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png",
      iconSize: [25, 41],
      iconAnchor: [12, 41],
      popupAnchor: [1, -34],
      shadowSize: [41, 41],
    });
  }, []);

  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold">Map</h2>
      </div>

      {validSelection && selected ? (
        <div className="h-[360px] w-full overflow-hidden border border-gray-400 bg-gray-100">
          <MapContainer
            center={[selected.latitude, selected.longitude]}
            zoom={PLACE_ZOOM}
            scrollWheelZoom
            className="h-full w-full"
            attributionControl
          >
            <TileLayer
              url={OSM_TILE_URL}
              attribution="&copy; OpenStreetMap contributors"
            />
            {naipImage && <NaipRasterOverlay image={naipImage} onError={onNaipError} />}
            <MapCenter selected={selected} />
            {markerIcon && (
              <Marker position={[selected.latitude, selected.longitude]} icon={markerIcon}>
                <Popup>{selected.display_name}</Popup>
              </Marker>
            )}
          </MapContainer>
        </div>
      ) : (
        <div
          role="status"
          className="flex h-[360px] w-full items-center justify-center border border-gray-400 bg-gray-100 px-4 text-center text-gray-700"
        >
          {selected
            ? "This location has invalid coordinates and cannot be shown on the map."
            : "Search for a location and select a result to display it on the map."}
        </div>
      )}
    </div>
  );
}
