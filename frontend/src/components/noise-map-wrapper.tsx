"use client";

import {
  MapContainer,
  TileLayer,
  CircleMarker,
  Popup,
  Tooltip,
} from "react-leaflet";
import type { NoiseStation } from "@/lib/types";
import { getNoiseComplianceColor, getNoiseComplianceLabel, ZONE_DISPLAY } from "@/lib/types";

interface NoiseMapWrapperProps {
  stations: NoiseStation[];
  onStationClick?: (stationId: string) => void;
  selectedStationId?: string | null;
  center: [number, number];
  zoom: number;
}

export default function NoiseMapWrapper({
  stations,
  onStationClick,
  selectedStationId,
  center,
  zoom,
}: NoiseMapWrapperProps) {
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
        url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
      />
      {stations.map((station) => {
        const color = getNoiseComplianceColor(station.leq, station.active_limit);
        const label = getNoiseComplianceLabel(station.leq, station.active_limit);
        const zone = ZONE_DISPLAY[station.zone] || { label: station.zone, color: "#6b7280" };
        const isSelected = station.station_id === selectedStationId;

        return (
          <CircleMarker
            key={station.station_id}
            center={[station.latitude, station.longitude]}
            radius={isSelected ? 10 : 7}
            pathOptions={{
              color: isSelected ? "#1e293b" : "#fff",
              fillColor: color,
              fillOpacity: 0.9,
              weight: isSelected ? 2.5 : 1.5,
              opacity: 0.95,
            }}
            eventHandlers={{
              click: () => onStationClick?.(station.station_id),
            }}
          >
            <Tooltip direction="top" offset={[0, -8]} opacity={0.95}>
              <div className="text-sm min-w-[140px]">
                <div className="font-bold" style={{ color }}>
                  {station.leq} dB(A)
                </div>
                <div className="font-medium">{station.station_name}</div>
                <div className="text-xs opacity-75">{station.city}</div>
                <div className="flex items-center gap-1 mt-0.5">
                  <span
                    className="inline-block w-2 h-2 rounded-full"
                    style={{ backgroundColor: zone.color }}
                  />
                  <span className="text-xs">{zone.label} Zone</span>
                </div>
                <div className="text-xs mt-0.5" style={{ color }}>
                  {label} (Limit: {station.active_limit} dB)
                </div>
              </div>
            </Tooltip>
            <Popup>
              <div className="min-w-[200px]">
                <h3 className="font-bold text-base mb-0.5">
                  {station.station_name}
                </h3>
                <p className="text-xs opacity-60 mb-2">
                  {station.station_id} &middot; {station.city}
                </p>

                {/* Zone badge */}
                <span
                  className="inline-block px-2 py-0.5 rounded text-white text-xs font-medium mb-2"
                  style={{ backgroundColor: zone.color }}
                >
                  {zone.label} Zone
                </span>

                {/* Readings */}
                <div className="grid grid-cols-3 gap-1 text-center mb-2">
                  <div className="bg-gray-50 rounded p-1">
                    <div className="text-xs text-gray-500">Leq</div>
                    <div className="font-bold text-sm">{station.leq}</div>
                  </div>
                  <div className="bg-gray-50 rounded p-1">
                    <div className="text-xs text-gray-500">Lmax</div>
                    <div className="font-bold text-sm">{station.lmax}</div>
                  </div>
                  <div className="bg-gray-50 rounded p-1">
                    <div className="text-xs text-gray-500">Lmin</div>
                    <div className="font-bold text-sm">{station.lmin}</div>
                  </div>
                </div>

                {/* Compliance */}
                <div
                  className="inline-block px-2 py-1 rounded text-white text-xs font-bold"
                  style={{ backgroundColor: color }}
                >
                  {label}
                  {station.exceedance_db > 0 && ` (+${station.exceedance_db} dB)`}
                </div>

                <div className="text-xs mt-1.5 opacity-50">
                  Limit: {station.active_limit} dB ({station.period})
                  &nbsp;|&nbsp; Day: {station.day_limit} / Night: {station.night_limit}
                </div>

                <p className="text-xs mt-1 opacity-40">
                  {new Date(station.timestamp).toLocaleString()}
                </p>
              </div>
            </Popup>
          </CircleMarker>
        );
      })}
    </MapContainer>
  );
}
