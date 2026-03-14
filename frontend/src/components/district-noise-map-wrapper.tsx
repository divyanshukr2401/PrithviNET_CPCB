"use client";

import {
  MapContainer,
  TileLayer,
  CircleMarker,
  Popup,
  Tooltip,
} from "react-leaflet";
import type { DistrictNoiseData } from "@/lib/types";
import {
  getDistrictNoiseMarkerColor,
  ZONE_DISPLAY,
  RISK_LEVEL_COLORS,
  COMPLIANCE_COLORS,
} from "@/lib/types";

interface DistrictNoiseMapWrapperProps {
  districts: DistrictNoiseData[];
  onDistrictClick?: (districtId: string) => void;
  selectedDistrictId?: string | null;
  center: [number, number];
  zoom: number;
}

export default function DistrictNoiseMapWrapper({
  districts,
  onDistrictClick,
  selectedDistrictId,
  center,
  zoom,
}: DistrictNoiseMapWrapperProps) {
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
      {districts.map((d) => {
        const color = getDistrictNoiseMarkerColor(d);
        const zoneConf = ZONE_DISPLAY[d.zone_type.toLowerCase()] || {
          label: d.zone_type,
          color: "#6b7280",
        };
        const isSelected = d.district_id === selectedDistrictId;

        return (
          <CircleMarker
            key={d.district_id}
            center={[d.latitude, d.longitude]}
            radius={isSelected ? 10 : 6}
            pathOptions={{
              color: isSelected ? "#1e293b" : "#fff",
              fillColor: color,
              fillOpacity: 0.85,
              weight: isSelected ? 2.5 : 1.5,
              opacity: 0.9,
            }}
            eventHandlers={{
              click: () => onDistrictClick?.(d.district_id),
            }}
          >
            <Tooltip direction="top" offset={[0, -8]} opacity={0.95}>
              <div className="text-sm min-w-[160px]">
                <div className="font-bold">{d.city_town}</div>
                <div className="text-xs opacity-75">
                  {d.district}, {d.state}
                </div>
                <div className="flex items-center gap-1 mt-0.5">
                  <span
                    className="inline-block w-2 h-2 rounded-full"
                    style={{ backgroundColor: zoneConf.color }}
                  />
                  <span className="text-xs">{zoneConf.label} Zone</span>
                </div>
                <div className="mt-0.5 text-xs">
                  <span className="font-medium">Leq 24hr:</span>{" "}
                  <span style={{ color }}>{d.leq_24hr_dba} dB(A)</span>
                </div>
                <div className="text-xs" style={{ color }}>
                  Risk: {d.risk_level}
                </div>
              </div>
            </Tooltip>
            <Popup>
              <div className="min-w-[220px]">
                <h3 className="font-bold text-base mb-0.5">{d.city_town}</h3>
                <p className="text-xs opacity-60 mb-1">
                  {d.district}, {d.state} &middot; {d.district_id}
                </p>

                {/* Zone + Risk badges */}
                <div className="flex gap-1 mb-2 flex-wrap">
                  <span
                    className="inline-block px-1.5 py-0.5 rounded text-white text-[10px] font-medium"
                    style={{ backgroundColor: zoneConf.color }}
                  >
                    {zoneConf.label}
                  </span>
                  <span
                    className="inline-block px-1.5 py-0.5 rounded text-white text-[10px] font-bold"
                    style={{ backgroundColor: color }}
                  >
                    {d.risk_level} Risk
                  </span>
                </div>

                {/* Key metrics */}
                <div className="grid grid-cols-3 gap-1 text-center mb-2">
                  <div className="bg-gray-50 rounded p-1">
                    <div className="text-[10px] text-gray-500">Lday</div>
                    <div className="font-bold text-xs">{d.lday_dba}</div>
                  </div>
                  <div className="bg-gray-50 rounded p-1">
                    <div className="text-[10px] text-gray-500">Lnight</div>
                    <div className="font-bold text-xs">{d.lnight_dba}</div>
                  </div>
                  <div className="bg-gray-50 rounded p-1">
                    <div className="text-[10px] text-gray-500">Lmax</div>
                    <div className="font-bold text-xs">{d.lmax_dba}</div>
                  </div>
                </div>

                {/* Compliance */}
                <div className="flex gap-1 text-[10px]">
                  <span>Day:</span>
                  <span
                    className="font-bold"
                    style={{
                      color:
                        COMPLIANCE_COLORS[d.compliance_day] || "#6b7280",
                    }}
                  >
                    {d.compliance_day}
                  </span>
                  <span className="mx-1">|</span>
                  <span>Night:</span>
                  <span
                    className="font-bold"
                    style={{
                      color:
                        COMPLIANCE_COLORS[d.compliance_night] || "#6b7280",
                    }}
                  >
                    {d.compliance_night}
                  </span>
                </div>

                <p className="text-[10px] mt-1 opacity-40">
                  Source: {d.data_source} ({d.year || "—"})
                </p>
              </div>
            </Popup>
          </CircleMarker>
        );
      })}
    </MapContainer>
  );
}
