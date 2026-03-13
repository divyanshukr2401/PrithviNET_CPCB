"use client";

import {
  MapContainer,
  TileLayer,
  CircleMarker,
  Popup,
  Tooltip,
} from "react-leaflet";
import MarkerClusterGroup from "react-leaflet-cluster";
import L from "leaflet";
import "leaflet.markercluster";
import type { AirReading } from "@/lib/types";
import { getAQIColor as canonicalAQIColor } from "@/lib/types";

interface LeafletMapWrapperProps {
  aqiReadings: AirReading[];
  center: [number, number];
  zoom: number;
  onStationClick?: (stationId: string) => void;
  getAQIColor: (aqi: number) => string;
  getAQICategory: (aqi: number) => string;
}

/**
 * Compute weighted average AQI color for a cluster of markers.
 */
function getClusterAverageAQI(cluster: L.MarkerCluster): number {
  const markers = cluster.getAllChildMarkers();
  let total = 0;
  let count = 0;
  for (const m of markers) {
    const aqi = (m.options as unknown as { aqiValue?: number }).aqiValue;
    if (aqi != null) {
      total += aqi;
      count++;
    }
  }
  return count > 0 ? Math.round(total / count) : 0;
}

/**
 * Custom cluster icon that shows count + average AQI color
 */
function createClusterIcon(cluster: L.MarkerCluster): L.DivIcon {
  const avgAqi = getClusterAverageAQI(cluster);
  const color = canonicalAQIColor(avgAqi);
  const count = cluster.getChildCount();
  const size = count < 10 ? 36 : count < 50 ? 44 : 52;

  return L.divIcon({
    html: `<div style="
      background: ${color};
      color: #fff;
      width: ${size}px;
      height: ${size}px;
      border-radius: 50%;
      display: flex;
      align-items: center;
      justify-content: center;
      font-weight: bold;
      font-size: ${size < 40 ? 12 : 14}px;
      border: 3px solid rgba(255,255,255,0.5);
      box-shadow: 0 2px 8px rgba(0,0,0,0.4);
    ">${count}</div>`,
    className: "custom-cluster-icon",
    iconSize: L.point(size, size),
    iconAnchor: L.point(size / 2, size / 2),
  });
}

export default function LeafletMapWrapper({
  aqiReadings,
  center,
  zoom,
  onStationClick,
  getAQIColor,
  getAQICategory,
}: LeafletMapWrapperProps) {
  return (
    <MapContainer
      center={center}
      zoom={zoom}
      className="w-full h-full"
      style={{ minHeight: "400px" }}
      zoomControl={true}
      scrollWheelZoom={true}
      preferCanvas={true}
    >
      <TileLayer
        attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OSM</a>'
        url="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png"
      />
      <MarkerClusterGroup
        chunkedLoading
        maxClusterRadius={50}
        spiderfyOnMaxZoom={true}
        showCoverageOnHover={false}
        disableClusteringAtZoom={10}
        iconCreateFunction={createClusterIcon}
      >
        {aqiReadings.map((reading) => {
          const color = getAQIColor(reading.aqi);
          const category = getAQICategory(reading.aqi);
          const radius = Math.max(6, Math.min(14, reading.aqi / 30 + 5));
          return (
            <CircleMarker
              key={reading.station_id}
              center={[reading.latitude, reading.longitude]}
              radius={radius}
              pathOptions={{
                color: color,
                fillColor: color,
                fillOpacity: 0.7,
                weight: 2,
                opacity: 0.9,
              }}
              // Store AQI for cluster calculation
              {...({ aqiValue: reading.aqi } as unknown as Record<string, unknown>)}
              eventHandlers={{
                click: () => onStationClick?.(reading.station_id),
              }}
            >
              <Tooltip direction="top" offset={[0, -8]} opacity={0.95}>
                <div className="text-sm">
                  <div className="font-bold" style={{ color }}>
                    AQI: {reading.aqi}
                  </div>
                  <div>{reading.city}</div>
                  <div className="text-xs opacity-75">{category}</div>
                </div>
              </Tooltip>
              <Popup>
                <div className="min-w-[180px]">
                  <h3 className="font-bold text-base mb-1">{reading.city}</h3>
                  <p className="text-xs opacity-70 mb-2">
                    {reading.station_id}
                  </p>
                  <div
                    className="inline-block px-2 py-1 rounded text-white text-sm font-bold"
                    style={{ backgroundColor: color }}
                  >
                    AQI: {reading.aqi} - {category}
                  </div>
                  <p className="text-xs mt-2 opacity-60">
                    {new Date(reading.timestamp).toLocaleTimeString()}
                  </p>
                </div>
              </Popup>
            </CircleMarker>
          );
        })}
      </MarkerClusterGroup>
    </MapContainer>
  );
}
