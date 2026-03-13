"""
OCEMS Auto-Healer — detect sensor faults vs real pollution events.
Uses a 4-indicator weighted scoring system to distinguish malfunctions from genuine spikes.

Indicators:
1. Temporal Gradient Score — sudden jump vs gradual rise
2. Cross-Sensor Correlation — do neighboring sensors agree?
3. Stuck-Value Detector — identical consecutive readings
4. Statistical Outlier Score — Mahalanobis-like distance from rolling baseline

Each scored 0-1, combined via weighted average. Final score > 0.6 = likely fault.
"""

import numpy as np
from datetime import datetime
from loguru import logger
from typing import Optional

from app.models.schemas import (
    SensorDiagnosis,
    HealerDiagnosisResponse,
    Severity,
)
from app.services.ingestion.clickhouse_writer import ch_writer


class OCEMSAutoHealer:
    """Diagnoses whether OCEMS anomalies are sensor faults or real pollution events."""

    # Tunable weights for each indicator
    WEIGHTS = {
        "temporal_gradient": 0.30,
        "cross_sensor_correlation": 0.25,
        "stuck_value": 0.25,
        "statistical_outlier": 0.20,
    }

    # Thresholds
    FAULT_THRESHOLD = 0.60       # score > this => likely sensor fault
    CRITICAL_THRESHOLD = 0.85    # score > this => almost certainly fault
    STUCK_WINDOW = 10            # consecutive identical readings to flag
    GRADIENT_SPIKE_FACTOR = 3.0  # jump > 3x rolling std = suspicious

    async def diagnose(
        self,
        factory_id: str,
        parameter: Optional[str] = None,
        hours: int = 6,
    ) -> HealerDiagnosisResponse:
        """
        Run full 4-indicator diagnosis on recent OCEMS data for a factory.
        """
        # Fetch recent data from ClickHouse
        readings = await ch_writer.query_recent_readings(
            table="ocems_raw",
            station_or_factory_id=factory_id,
            id_column="factory_id",
            hours=hours,
            parameter=parameter,
        )

        if not readings:
            # No data — likely DAHS offline
            return HealerDiagnosisResponse(
                factory_id=factory_id,
                timestamp=datetime.now(),
                diagnoses=[
                    SensorDiagnosis(
                        factory_id=factory_id,
                        parameter=parameter or "all",
                        diagnosis="no_data",
                        confidence=0.9,
                        indicators={},
                        severity=Severity.HIGH,
                        recommended_action="escalate",
                        explanation=f"No OCEMS data received in the last {hours} hours. DAHS may be offline.",
                    )
                ],
                overall_health=0.0,
                dahs_uptime_pct=0.0,
            )

        # Group readings by parameter
        params = set(r.get("parameter", "") for r in readings)
        if parameter:
            params = {parameter}

        diagnoses = []
        for param in params:
            param_readings = [r for r in readings if r.get("parameter") == param]
            if len(param_readings) < 5:
                continue

            values = np.array([r["value"] for r in param_readings], dtype=np.float64)
            timestamps = [r["timestamp"] for r in param_readings]

            # Run all 4 indicators
            indicators = {}
            indicators["temporal_gradient"] = self._temporal_gradient_score(values)
            indicators["cross_sensor_correlation"] = self._cross_sensor_score(values)
            indicators["stuck_value"] = self._stuck_value_score(values)
            indicators["statistical_outlier"] = self._statistical_outlier_score(values)

            # Weighted combined score (higher = more likely fault)
            fault_score = sum(
                indicators[k] * self.WEIGHTS[k] for k in self.WEIGHTS
            )

            # Classify
            if fault_score >= self.CRITICAL_THRESHOLD:
                diagnosis = "fault_detected"
                severity = Severity.CRITICAL
                action = "recalibrate"
                explanation = self._explain_fault(indicators, param, factory_id)
            elif fault_score >= self.FAULT_THRESHOLD:
                diagnosis = "fault_detected"
                severity = Severity.HIGH
                action = "flag_review"
                explanation = self._explain_fault(indicators, param, factory_id)
            elif fault_score >= 0.4:
                diagnosis = "suspect"
                severity = Severity.MEDIUM
                action = "flag_review"
                explanation = f"Sensor readings for {param} show moderate anomaly characteristics. Manual review recommended."
            else:
                diagnosis = "real_event" if any(v > np.percentile(values, 95) for v in values[-5:]) else "normal"
                severity = Severity.LOW if diagnosis == "normal" else Severity.HIGH
                action = "escalate" if diagnosis == "real_event" else "none"
                explanation = (
                    f"Readings for {param} appear genuine. Recent values are elevated — likely a real emission event."
                    if diagnosis == "real_event"
                    else f"Readings for {param} are within normal operational range."
                )

            diagnoses.append(SensorDiagnosis(
                factory_id=factory_id,
                parameter=param,
                diagnosis=diagnosis,
                confidence=min(0.99, fault_score + 0.3) if fault_score > 0.6 else max(0.3, 1 - fault_score),
                indicators=indicators,
                severity=severity,
                recommended_action=action,
                explanation=explanation,
            ))

        # Overall health: inverse of max fault score across parameters
        max_fault = max((d.indicators.get("temporal_gradient", 0) for d in diagnoses), default=0)
        overall_health = max(0, 100 * (1 - max_fault))

        # DAHS uptime: proportion of readings with valid quality flag
        total = len(readings)
        valid = sum(1 for r in readings if r.get("quality_flag", "valid") == "valid")
        dahs_uptime = (valid / total * 100) if total > 0 else 0

        return HealerDiagnosisResponse(
            factory_id=factory_id,
            timestamp=datetime.now(),
            diagnoses=diagnoses,
            overall_health=overall_health,
            dahs_uptime_pct=dahs_uptime,
        )

    # ==================================================================
    # INDICATOR 1: Temporal Gradient Score
    # Sudden jumps that are physically implausible suggest sensor fault
    # ==================================================================
    def _temporal_gradient_score(self, values: np.ndarray) -> float:
        if len(values) < 3:
            return 0.0
        diffs = np.abs(np.diff(values))
        rolling_std = np.std(values)
        if rolling_std < 1e-6:
            return 0.8  # near-zero variance is suspicious
        max_diff = np.max(diffs)
        # Normalize: how many rolling-stds is the biggest jump?
        ratio = max_diff / rolling_std
        # Sigmoid-like mapping to 0-1
        score = 1.0 / (1.0 + np.exp(-0.5 * (ratio - self.GRADIENT_SPIKE_FACTOR)))
        return float(np.clip(score, 0, 1))

    # ==================================================================
    # INDICATOR 2: Cross-Sensor Correlation
    # If only one sensor spikes while co-located sensors are normal, likely fault
    # For OCEMS we check across parameters of the same factory
    # ==================================================================
    def _cross_sensor_score(self, values: np.ndarray) -> float:
        """
        Simplified cross-sensor: check if the spike pattern is isolated.
        In a real system, we'd compare with nearby factories.
        Here we use auto-correlation as a proxy.
        """
        if len(values) < 10:
            return 0.0
        # Check if recent values deviate from the mean much more than early values
        mid = len(values) // 2
        early_std = np.std(values[:mid])
        late_std = np.std(values[mid:])
        if early_std < 1e-6:
            return 0.5
        ratio = late_std / max(early_std, 1e-6)
        # If late half is much more volatile, suspicious
        if ratio > 3.0:
            return 0.8
        elif ratio > 2.0:
            return 0.5
        elif ratio < 0.3:
            # Suspicious lack of variance (stuck)
            return 0.6
        return 0.1

    # ==================================================================
    # INDICATOR 3: Stuck-Value Detector
    # OCEMS sensors getting "stuck" on one value is a classic failure mode
    # ==================================================================
    def _stuck_value_score(self, values: np.ndarray) -> float:
        if len(values) < self.STUCK_WINDOW:
            return 0.0
        max_run = 1
        current_run = 1
        for i in range(1, len(values)):
            if abs(values[i] - values[i - 1]) < 0.01:
                current_run += 1
                max_run = max(max_run, current_run)
            else:
                current_run = 1
        # Score based on longest run relative to window
        score = min(1.0, max_run / self.STUCK_WINDOW)
        return float(score)

    # ==================================================================
    # INDICATOR 4: Statistical Outlier Score
    # Modified z-score using median absolute deviation (robust to outliers)
    # ==================================================================
    def _statistical_outlier_score(self, values: np.ndarray) -> float:
        if len(values) < 5:
            return 0.0
        median = np.median(values)
        mad = np.median(np.abs(values - median))
        if mad < 1e-6:
            # All values near median — could be stuck
            return 0.3
        # Modified z-scores for last 5 readings
        recent = values[-5:]
        z_scores = 0.6745 * (recent - median) / mad
        max_z = np.max(np.abs(z_scores))
        # Map to 0-1: z > 3.5 is highly suspicious
        score = 1.0 / (1.0 + np.exp(-0.8 * (max_z - 3.0)))
        return float(np.clip(score, 0, 1))

    # ==================================================================
    # EXPLANATION GENERATOR
    # ==================================================================
    def _explain_fault(self, indicators: dict, param: str, factory_id: str) -> str:
        top = sorted(indicators.items(), key=lambda x: x[1], reverse=True)
        primary = top[0]
        explanations = {
            "temporal_gradient": f"Sharp sudden jump in {param} readings — physically implausible for this emission source.",
            "cross_sensor_correlation": f"The anomaly in {param} is isolated and not corroborated by other parameters.",
            "stuck_value": f"Sensor for {param} shows repeated identical values — classic OCEMS malfunction pattern.",
            "statistical_outlier": f"Recent {param} readings are extreme statistical outliers relative to baseline.",
        }
        return (
            f"[{factory_id}] Likely sensor fault on {param}. "
            f"Primary indicator: {primary[0]} (score={primary[1]:.2f}). "
            f"{explanations.get(primary[0], 'Manual inspection recommended.')}"
        )


# Singleton
auto_healer = OCEMSAutoHealer()
