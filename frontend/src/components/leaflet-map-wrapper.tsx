"use client";

import {
  MapContainer,
  TileLayer,
  CircleMarker,
  Popup,
  Tooltip,
} from "react-leaflet";
import type { AirReading } from "@/lib/types";

interface LeafletMapWrapperProps {
  aqiReadings: AirReading[];
  center: [number, number];
  zoom: number;
  onStationClick?: (stationId: string) => void;
  getAQIColor: (aqi: number) => string;
  getAQICategory: (aqi: number) => string;
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
    >
      <TileLayer
        attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OSM</a>'
        url="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png"
      />
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
    </MapContainer>
  );
}
