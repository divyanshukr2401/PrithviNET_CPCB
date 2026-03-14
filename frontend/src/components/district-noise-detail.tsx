"use client";

import { X } from "lucide-react";
import type { DistrictNoiseData } from "@/lib/types";
import {
  ZONE_DISPLAY,
  RISK_LEVEL_COLORS,
  COMPLIANCE_COLORS,
} from "@/lib/types";

interface DistrictNoiseDetailProps {
  district: DistrictNoiseData;
  onClose: () => void;
}

export function DistrictNoiseDetail({
  district: d,
  onClose,
}: DistrictNoiseDetailProps) {
  const zoneConf = ZONE_DISPLAY[d.zone_type.toLowerCase()] || {
    label: d.zone_type,
    color: "#6b7280",
  };
  const riskColor = RISK_LEVEL_COLORS[d.risk_level] || "#6b7280";
  const compDayColor = COMPLIANCE_COLORS[d.compliance_day] || "#6b7280";
  const compNightColor = COMPLIANCE_COLORS[d.compliance_night] || "#6b7280";

  return (
    <div className="flex flex-col h-full overflow-y-auto">
      {/* Header */}
      <div className="p-3 border-b border-border flex items-center justify-between">
        <div className="min-w-0">
          <h3 className="text-sm font-bold truncate">{d.city_town}</h3>
          <p className="text-xs text-muted-foreground truncate">
            {d.district}, {d.state}
          </p>
        </div>
        <button
          onClick={onClose}
          className="p-1 rounded-md hover:bg-muted/50 transition-colors flex-shrink-0"
        >
          <X className="w-4 h-4" />
        </button>
      </div>

      {/* Badges */}
      <div className="p-3 flex items-center gap-2 flex-wrap">
        <span
          className="px-2 py-0.5 rounded text-white text-xs font-medium"
          style={{ backgroundColor: zoneConf.color }}
        >
          {zoneConf.label} Zone
        </span>
        <span
          className="px-2 py-0.5 rounded text-white text-xs font-bold"
          style={{ backgroundColor: riskColor }}
        >
          {d.risk_level} Risk
        </span>
        <span className="text-[10px] text-muted-foreground ml-auto">
          {d.district_id}
        </span>
      </div>

      {/* Noise Level Metrics */}
      <div className="px-3 pb-3">
        <h4 className="text-xs font-medium text-muted-foreground mb-2">
          Noise Levels
        </h4>
        <div className="grid grid-cols-3 gap-2">
          <div className="bg-muted/30 rounded-lg p-2 text-center">
            <div className="text-[10px] text-muted-foreground">Lday</div>
            <div className="text-lg font-bold">{d.lday_dba}</div>
            <div className="text-[10px] text-muted-foreground">dB(A)</div>
          </div>
          <div className="bg-muted/30 rounded-lg p-2 text-center">
            <div className="text-[10px] text-muted-foreground">Lnight</div>
            <div className="text-lg font-bold">{d.lnight_dba}</div>
            <div className="text-[10px] text-muted-foreground">dB(A)</div>
          </div>
          <div className="bg-muted/30 rounded-lg p-2 text-center">
            <div className="text-[10px] text-muted-foreground">Leq 24hr</div>
            <div className="text-lg font-bold">{d.leq_24hr_dba}</div>
            <div className="text-[10px] text-muted-foreground">dB(A)</div>
          </div>
        </div>
        <div className="grid grid-cols-2 gap-2 mt-2">
          <div className="bg-muted/30 rounded-lg p-2 text-center">
            <div className="text-[10px] text-muted-foreground">Lden</div>
            <div className="text-lg font-bold">{d.lden_dba}</div>
            <div className="text-[10px] text-muted-foreground">dB(A)</div>
          </div>
          <div className="bg-muted/30 rounded-lg p-2 text-center">
            <div className="text-[10px] text-muted-foreground">Lmax</div>
            <div className="text-lg font-bold" style={{ color: d.lmax_dba >= 90 ? "#dc2626" : undefined }}>
              {d.lmax_dba}
            </div>
            <div className="text-[10px] text-muted-foreground">dB(A)</div>
          </div>
        </div>
      </div>

      {/* CPCB Standards & Exceedance */}
      <div className="px-3 pb-3">
        <h4 className="text-xs font-medium text-muted-foreground mb-2">
          CPCB Standards & Exceedance
        </h4>
        <div className="bg-muted/20 rounded-lg overflow-hidden">
          <table className="w-full text-xs">
            <thead>
              <tr className="border-b border-border/50">
                <th className="py-1.5 px-2 text-left font-medium text-muted-foreground" />
                <th className="py-1.5 px-2 text-center font-medium text-muted-foreground">
                  Day
                </th>
                <th className="py-1.5 px-2 text-center font-medium text-muted-foreground">
                  Night
                </th>
              </tr>
            </thead>
            <tbody>
              <tr className="border-b border-border/30">
                <td className="py-1.5 px-2 text-muted-foreground">Standard</td>
                <td className="py-1.5 px-2 text-center font-medium">
                  {d.std_day_db} dB
                </td>
                <td className="py-1.5 px-2 text-center font-medium">
                  {d.std_night_db} dB
                </td>
              </tr>
              <tr className="border-b border-border/30">
                <td className="py-1.5 px-2 text-muted-foreground">Measured</td>
                <td className="py-1.5 px-2 text-center font-medium">
                  {d.lday_dba} dB
                </td>
                <td className="py-1.5 px-2 text-center font-medium">
                  {d.lnight_dba} dB
                </td>
              </tr>
              <tr className="border-b border-border/30">
                <td className="py-1.5 px-2 text-muted-foreground">
                  Exceedance
                </td>
                <td className="py-1.5 px-2 text-center font-bold"
                    style={{ color: d.exceed_day_db > 0 ? "#dc2626" : "#16a34a" }}>
                  {d.exceed_day_db > 0 ? `+${d.exceed_day_db}` : d.exceed_day_db} dB
                </td>
                <td className="py-1.5 px-2 text-center font-bold"
                    style={{ color: d.exceed_night_db > 0 ? "#dc2626" : "#16a34a" }}>
                  {d.exceed_night_db > 0 ? `+${d.exceed_night_db}` : d.exceed_night_db} dB
                </td>
              </tr>
              <tr>
                <td className="py-1.5 px-2 text-muted-foreground">
                  Compliance
                </td>
                <td className="py-1.5 px-2 text-center">
                  <span
                    className="inline-block px-1.5 py-0.5 rounded text-white text-[10px] font-bold"
                    style={{ backgroundColor: compDayColor }}
                  >
                    {d.compliance_day}
                  </span>
                </td>
                <td className="py-1.5 px-2 text-center">
                  <span
                    className="inline-block px-1.5 py-0.5 rounded text-white text-[10px] font-bold"
                    style={{ backgroundColor: compNightColor }}
                  >
                    {d.compliance_night}
                  </span>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      {/* Noise Source */}
      <div className="px-3 pb-3">
        <h4 className="text-xs font-medium text-muted-foreground mb-1">
          Primary Noise Source
        </h4>
        <p className="text-sm">{d.primary_noise_source}</p>
      </div>

      {/* Data Source & Year */}
      <div className="px-3 pb-3">
        <h4 className="text-xs font-medium text-muted-foreground mb-1">
          Data Source
        </h4>
        <p className="text-sm">
          {d.data_source}
          {d.year && <span className="text-muted-foreground"> ({d.year})</span>}
        </p>
      </div>

      {/* Notes */}
      {d.notes && (
        <div className="px-3 pb-3">
          <h4 className="text-xs font-medium text-muted-foreground mb-1">
            Notes
          </h4>
          <p className="text-xs text-muted-foreground italic">{d.notes}</p>
        </div>
      )}

      {/* Coordinates */}
      <div className="px-3 pb-3 text-[10px] text-muted-foreground text-right mt-auto">
        {d.latitude.toFixed(4)}&deg;N, {d.longitude.toFixed(4)}&deg;E
      </div>
    </div>
  );
}
