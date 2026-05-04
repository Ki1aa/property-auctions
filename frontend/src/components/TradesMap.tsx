import { useEffect, useRef } from "react";
import maplibregl from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";
import { MapPoint } from "../types";

type Props = {
  points: MapPoint[];
  height?: string;
  fitToPoints?: boolean;
};

const RU_CENTER: [number, number] = [73.0, 61.0];

export function TradesMap({ points, height = "420px", fitToPoints = true }: Props) {
  const mapContainerRef = useRef<HTMLDivElement | null>(null);
  const mapRef = useRef<maplibregl.Map | null>(null);
  const markersRef = useRef<maplibregl.Marker[]>([]);

  useEffect(() => {
    if (!mapContainerRef.current || mapRef.current) {
      return;
    }

    mapRef.current = new maplibregl.Map({
      container: mapContainerRef.current,
      style: "https://demotiles.maplibre.org/style.json",
      center: RU_CENTER,
      zoom: 3,
    });

    mapRef.current.addControl(new maplibregl.NavigationControl(), "top-right");

    return () => {
      markersRef.current.forEach((marker) => marker.remove());
      markersRef.current = [];
      mapRef.current?.remove();
      mapRef.current = null;
    };
  }, []);

  useEffect(() => {
    const map = mapRef.current;
    if (!map) {
      return;
    }

    markersRef.current.forEach((marker) => marker.remove());
    markersRef.current = [];

    for (const point of points) {
      const popup = new maplibregl.Popup({ offset: 20 }).setHTML(
        `<strong>${point.title}</strong><br/>Статус: ${point.status || "—"}`
      );

      const marker = new maplibregl.Marker({ color: "#d23f31" })
        .setLngLat([point.longitude, point.latitude])
        .setPopup(popup)
        .addTo(map);

      markersRef.current.push(marker);
    }

    if (!fitToPoints || points.length === 0) {
      return;
    }

    if (points.length === 1) {
      map.flyTo({ center: [points[0].longitude, points[0].latitude], zoom: 11, essential: true });
      return;
    }

    const bounds = new maplibregl.LngLatBounds();
    for (const point of points) {
      bounds.extend([point.longitude, point.latitude]);
    }
    map.fitBounds(bounds, { padding: 60, duration: 600, maxZoom: 9 });
  }, [points, fitToPoints]);

  return <div ref={mapContainerRef} style={{ height, width: "100%", borderRadius: "12px", overflow: "hidden" }} />;
}
