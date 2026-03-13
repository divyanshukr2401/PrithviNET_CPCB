"""
PRITHVINET Pydantic Models
==========================
Shared data models for API requests/responses, ingestion, and inter-service communication.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Optional
from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class StationType(str, Enum):
    AIR = "air"
    WATER = "water"
    NOISE = "noise"


class ZoneType(str, Enum):
    INDUSTRIAL = "industrial"
    COMMERCIAL = "commercial"
    RESIDENTIAL = "residential"
    SILENCE = "silence"
    RIVERFRONT = "riverfront"
    MINING = "mining"


class QualityFlag(str, Enum):
    VALID = "valid"
    SUSPECT = "suspect"
    INVALID = "invalid"
    MISSING = "missing"


class AnomalyType(str, Enum):
    NONE = ""
    SPIKE = "spike"
    STUCK = "stuck"
    DRIFT = "drift"
    DROPOUT = "dropout"
    CALIBRATION = "calibration"
    FLATLINE = "flatline"


class Severity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


# ---------------------------------------------------------------------------
# INGESTION MODELS — what the simulator POSTs to the backend
# ---------------------------------------------------------------------------


class AirQualityReading(BaseModel):
    station_id: str
    timestamp: datetime
    parameter: str  # PM2.5, PM10, NO2, SO2, CO, O3, NH3, Pb
    value: float
    unit: str = "µg/m³"
    aqi: int = 0
    city: str
    latitude: float
    longitude: float
    zone: ZoneType
    is_anomaly: bool = False
    anomaly_type: AnomalyType = AnomalyType.NONE
    quality_flag: QualityFlag = QualityFlag.VALID


class WaterQualityReading(BaseModel):
    station_id: str
    timestamp: datetime
    parameter: str  # pH, DO, BOD, COD, TSS, Turbidity, Conductivity, Temperature, Nitrates, Phosphates
    value: float
    unit: str
    wqi: float = 0.0
    river_name: str = ""
    city: str
    latitude: float
    longitude: float
    is_anomaly: bool = False
    anomaly_type: AnomalyType = AnomalyType.NONE
    quality_flag: QualityFlag = QualityFlag.VALID


class NoiseReading(BaseModel):
    station_id: str
    timestamp: datetime
    metric: str  # Leq, Lmax, Lmin, L10, L50, L90, Lden
    value: float  # dB(A)
    city: str
    latitude: float
    longitude: float
    zone: ZoneType
    day_limit: float
    night_limit: float
    is_exceedance: bool = False
    is_anomaly: bool = False
    anomaly_type: AnomalyType = AnomalyType.NONE
    quality_flag: QualityFlag = QualityFlag.VALID


class OCEMSReading(BaseModel):
    factory_id: str
    timestamp: datetime
    parameter: str  # PM, SO2, NOx, CO
    value: float  # mg/Nm³
    unit: str = "mg/Nm³"
    emission_limit: float
    exceedance_pct: float = 0.0
    industry_type: str
    city: str
    latitude: float
    longitude: float
    dahs_status: str = "online"
    sensor_health: float = 100.0
    is_anomaly: bool = False
    anomaly_type: AnomalyType = AnomalyType.NONE
    quality_flag: QualityFlag = QualityFlag.VALID


# ---------------------------------------------------------------------------
# BATCH INGESTION — for bulk historical data loading
# ---------------------------------------------------------------------------


class BatchIngestRequest(BaseModel):
    """Batch of readings for bulk ingestion."""

    air_readings: list[AirQualityReading] = []
    water_readings: list[WaterQualityReading] = []
    noise_readings: list[NoiseReading] = []
    ocems_readings: list[OCEMSReading] = []


class IngestResponse(BaseModel):
    status: str = "ok"
    inserted: int = 0
    errors: int = 0
    message: str = ""


# ---------------------------------------------------------------------------
# OCEMS AUTO-HEALER
# ---------------------------------------------------------------------------


class SensorDiagnosis(BaseModel):
    factory_id: str
    parameter: str
    diagnosis: str  # fault_detected, real_event, normal
    confidence: float = Field(ge=0, le=1)
    indicators: dict[str, float] = {}  # individual indicator scores
    severity: Severity = Severity.LOW
    recommended_action: str = "none"  # none, recalibrate, flag_review, escalate
    explanation: str = ""


class HealerDiagnosisResponse(BaseModel):
    factory_id: str
    timestamp: datetime
    diagnoses: list[SensorDiagnosis]
    overall_health: float = Field(ge=0, le=100)
    dahs_uptime_pct: float = Field(ge=0, le=100)


# ---------------------------------------------------------------------------
# FORECASTING
# ---------------------------------------------------------------------------


class ForecastRequest(BaseModel):
    station_id: str
    parameter: str
    horizon_hours: int = Field(default=24, ge=1, le=72)
    confidence_levels: list[float] = [0.5, 0.9]  # 50% and 90% CI


class ForecastPoint(BaseModel):
    target_time: datetime
    predicted_mean: float
    predicted_lo90: float
    predicted_hi90: float
    predicted_lo50: float
    predicted_hi50: float


class ForecastResponse(BaseModel):
    station_id: str
    parameter: str
    model_name: str
    created_at: datetime
    horizon_hours: int
    forecasts: list[ForecastPoint]
    model_metrics: dict[str, Any] = {}  # MAE, RMSE, CRPS, method name, etc.


# ---------------------------------------------------------------------------
# CAUSAL / POLICY SIMULATION (NumPy SEM)
# ---------------------------------------------------------------------------


class PolicyIntervention(BaseModel):
    """Describes a what-if policy intervention."""

    intervention_type: (
        str  # e.g., "industry_emission_cap", "traffic_restriction", "green_belt"
    )
    city: str = "Raipur"
    target_parameter: str = "PM2.5"
    reduction_pct: float = Field(default=20.0, ge=0, le=100)
    description: str = ""


class CausalEffect(BaseModel):
    baseline_value: float
    counterfactual_value: float
    absolute_effect: float
    relative_effect_pct: float
    confidence_interval: tuple[float, float]
    p_value: float


class PolicySimulationResponse(BaseModel):
    intervention: PolicyIntervention
    effects: dict[str, CausalEffect]  # parameter -> effect
    dag_edges: list[tuple[str, str]]  # causal DAG edges
    robustness_checks: dict[str, float] = {}
    explanation: str = ""


# ---------------------------------------------------------------------------
# GAMIFICATION
# ---------------------------------------------------------------------------


class UserProfile(BaseModel):
    user_id: str
    username: str
    city: str
    eco_points: int = 0
    level: int = 1
    badges: list[str] = []
    rank: Optional[int] = None


class EcoPointTransaction(BaseModel):
    user_id: str
    points: int
    action: (
        str  # air_report, water_report, noise_report, green_commute, challenge_complete
    )
    description: str = ""


class CitizenReport(BaseModel):
    user_id: str
    report_type: str  # air_pollution, water_pollution, noise_violation, illegal_dumping
    latitude: float
    longitude: float
    description: str
    severity: Severity = Severity.MEDIUM


class LeaderboardEntry(BaseModel):
    rank: int
    user_id: str
    username: str
    city: str
    eco_points: int
    level: int


# ---------------------------------------------------------------------------
# COMPLIANCE
# ---------------------------------------------------------------------------


class ComplianceStatus(BaseModel):
    factory_id: str
    factory_name: str
    industry_type: str
    city: str
    overall_compliance_pct: float
    parameters: dict[
        str, dict
    ]  # param -> {avg, max, limit, compliance_pct, exceedance_count}
    risk_level: Severity
    last_checked: datetime


class ComplianceSummary(BaseModel):
    total_factories: int
    compliant: int
    non_compliant: int
    critical: int
    overall_compliance_pct: float
    by_city: dict[str, float]  # city -> compliance %
    by_industry: dict[str, float]  # industry_type -> compliance %
