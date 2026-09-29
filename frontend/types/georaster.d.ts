declare module "georaster" {
  import type { GeoRaster } from "georaster-layer-for-leaflet";

  export default function parseGeoraster(data: ArrayBuffer): Promise<GeoRaster>;
}