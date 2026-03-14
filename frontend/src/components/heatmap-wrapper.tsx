"use client";

import { useEffect, useRef } from "react";
import {
  MapContainer,
  TileLayer,
  useMap,
} from "react-leaflet";
import L from "leaflet";
import "leaflet.heat";

export interface HeatmapPoint {
  lat: number;
  lng: number;
  intensity: number;
  station_name?: string;
  state?: string;
  parameters?: Record<string, number>;
}

interface HeatLayerControlProps {
  points: HeatmapPoint[];
  radius?: number;
  blur?: number;
  maxZoom?: number;
  max?: number;
  gradient?: Record<number, string>;
}

/**
 * Inner component that accesses the map instance via useMap()
 * and adds/updates the L.heatLayer.
 */
function HeatLayerControl({
  points,
  radius = 25,
  blur = 15,
  maxZoom = 18,
  max = 1.0,
  gradient,
}: HeatLayerControlProps) {
  const map = useMap();
  const heatLayerRef = useRef<L.HeatLayer | null>(null);

  useEffect(() => {
    if (!map) return;

    const heatData: L.HeatLatLngTuple[] = points.map((p) => [
      p.lat,
      p.lng,
      p.intensity,
    ]);

    const options: L.HeatLayerOptions = {
      radius,
      blur,
      maxZoom,
      max,
      minOpacity: 0.4,
    };

    if (gradient) {
      options.gradient = gradient;
    }

    if (heatLayerRef.current) {
      heatLayerRef.current.setLatLngs(heatData);
      heatLayerRef.current.setOptions(options);
    } else {
      heatLayerRef.current = L.heatLayer(heatData, options);
      heatLayerRef.current.addTo(map);
    }

    return () => {
      if (heatLayerRef.current) {
        map.removeLayer(heatLayerRef.current);
        heatLayerRef.current = null;
      }
    };
  }, [map, points, radius, blur, maxZoom, max, gradient]);

  return null;
}

interface HeatmapWrapperProps {
  points: HeatmapPoint[];
  center?: [number, number];
  zoom?: number;
  className?: string;
  radius?: number;
  blur?: number;
  max?: number;
  gradient?: Record<number, string>;
}

export default function HeatmapWrapper({
  points,
  center = [22.5, 80.0],
  zoom = 5,
  className = "",
  radius = 25,
  blur = 15,
  max = 1.0,
  gradient,
}: HeatmapWrapperProps) {
  return (
    <MapContainer
      center={center}
      zoom={zoom}
      className={`w-full h-full ${className}`}
      style={{ minHeight: "400px" }}
      zoomControl={true}
      scrollWheelZoom={true}
    >
      <TileLayer
        attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OSM</a>'
        url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
      />
      <HeatLayerControl
        points={points}
        radius={radius}
        blur={blur}
        max={max}
        gradient={gradient}
      />
    </MapContainer>
  );
}
