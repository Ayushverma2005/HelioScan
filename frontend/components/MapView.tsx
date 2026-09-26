"use client";

import { useEffect, useMemo } from "react";
import { MapContainer, Marker, Popup, TileLayer, useMap } from "react-leaflet";
import L from "leaflet";
import type { GeocodingResult } from "@/lib/geocode";
import "leaflet/dist/leaflet.css";

const PLACE_ZOOM = 12;
const OSM_TILE_URL = "https://tile.openstreetmap.org/{z}/{x}/{y}.png";

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

export default function MapView({ selected }: { selected: GeocodingResult | null }) {
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
