"""
Nixtla Probabilistic Forecaster — 24-72 hour forecasts with confidence intervals.
Uses Nixtla's TimeGPT API for zero-shot forecasting on air, water, and noise data.

Falls back to a simple exponential smoothing + bootstrap CI if Nixtla API is unavailable.
"""

import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from loguru import logger
from typing import Optional

from app.models.schemas import (
    ForecastRequest,
    ForecastPoint,
    ForecastResponse,
)
from app.services.ingestion.clickhouse_writer import ch_writer

# Try importing Nixtla — optional dependency
try:
    from nixtla import NixtlaClient

    NIXTLA_AVAILABLE = True
except ImportError:
    NIXTLA_AVAILABLE = False
    logger.warning("Nixtla not available — falling back to statistical forecasting")


class NixtlaForecaster:
    """Probabilistic time-series forecasting using Nixtla TimeGPT or statistical fallback."""

    # Table mapping for each data type
    TABLE_MAP = {
        "air": ("air_quality_raw", "parameter"),
        "water": ("water_quality_raw", "parameter"),
        "noise": ("noise_raw", "metric"),
    }

    def __init__(self, api_key: Optional[str] = None):
        self._client = None
        if NIXTLA_AVAILABLE and api_key:
            try:
                self._client = NixtlaClient(api_key=api_key)
                logger.info("Nixtla TimeGPT client initialized")
            except Exception as e:
                logger.warning(f"Failed to init Nixtla client: {e}")

    async def forecast(
        self,
        request: ForecastRequest,
        data_type: str = "air",  # air, water, noise
    ) -> ForecastResponse:
        """
        Generate probabilistic forecast for a station/parameter.
        """
        # Determine which table and column to query
        table, _ = self.TABLE_MAP.get(data_type, ("air_quality_raw", "parameter"))

        # Fetch historical data (30 days)
        series = await ch_writer.query_historical_series(
            table=table,
            station_id=request.station_id,
            parameter=request.parameter,
            days=30,
        )

        if len(series) < 24:
            # Not enough data — return simple persistence forecast
            return self._persistence_forecast(request, series)

        # Convert to DataFrame
        df = pd.DataFrame(series)
        df["timestamp"] = pd.to_datetime(df["timestamp"])
        df = df.sort_values("timestamp").reset_index(drop=True)

        # Try Nixtla first, fall back to statistical
        if self._client is not None:
            try:
                return await self._nixtla_forecast(df, request)
            except Exception as e:
                logger.warning(f"Nixtla forecast failed, using fallback: {e}")

        return self._statistical_forecast(df, request)

    # ==================================================================
    # NIXTLA TIMEGPT FORECASTING
    # ==================================================================
    async def _nixtla_forecast(
        self, df: pd.DataFrame, request: ForecastRequest
    ) -> ForecastResponse:
        """Use Nixtla TimeGPT for zero-shot probabilistic forecasting."""
        # Prepare data in Nixtla format
        nixtla_df = df.rename(columns={"timestamp": "ds", "value": "y"})
        nixtla_df["unique_id"] = f"{request.station_id}_{request.parameter}"

        # Determine frequency from data
        if len(nixtla_df) > 2:
            median_gap = nixtla_df["ds"].diff().median()
            if median_gap < timedelta(minutes=10):
                freq = "5min"  # Air quality: 5-min intervals
            elif median_gap < timedelta(hours=2):
                freq = "1h"  # Water: hourly
            else:
                freq = "1h"
        else:
            freq = "1h"

        # Calculate steps
        freq_minutes = {"5min": 5, "1h": 60}.get(freq, 60)
        steps = (request.horizon_hours * 60) // freq_minutes

        # Call TimeGPT
        forecast_df = self._client.forecast(
            df=nixtla_df,
            h=steps,
            level=[50, 90],
            freq=freq,
        )

        # Parse results
        forecasts = []
        for _, row in forecast_df.iterrows():
            forecasts.append(
                ForecastPoint(
                    target_time=row["ds"],
                    predicted_mean=float(row.get("TimeGPT", row.iloc[1])),
                    predicted_lo90=float(row.get("TimeGPT-lo-90", row.iloc[1] * 0.7)),
                    predicted_hi90=float(row.get("TimeGPT-hi-90", row.iloc[1] * 1.3)),
                    predicted_lo50=float(row.get("TimeGPT-lo-50", row.iloc[1] * 0.85)),
                    predicted_hi50=float(row.get("TimeGPT-hi-50", row.iloc[1] * 1.15)),
                )
            )

        return ForecastResponse(
            station_id=request.station_id,
            parameter=request.parameter,
            model_name="nixtla_timegpt",
            created_at=datetime.now(),
            horizon_hours=request.horizon_hours,
            forecasts=forecasts,
            model_metrics={"method": "timegpt_zero_shot"},
        )

    # ==================================================================
    # STATISTICAL FALLBACK: Exponential Smoothing + Bootstrap CIs
    # ==================================================================
    def _statistical_forecast(
        self, df: pd.DataFrame, request: ForecastRequest
    ) -> ForecastResponse:
        """
        Simple Holt-Winters-like exponential smoothing with bootstrap confidence intervals.
        Works without scipy/statsmodels (pure NumPy).
        """
        values = df["value"].values.astype(np.float64)
        timestamps = df["timestamp"].values

        # Estimate frequency
        if len(timestamps) > 2:
            median_gap = (
                np.median(np.diff(timestamps.astype(np.int64))) / 1e9
            )  # seconds
            freq_seconds = max(300, int(median_gap))  # minimum 5 min
        else:
            freq_seconds = 3600

        steps = (request.horizon_hours * 3600) // freq_seconds

        # Double exponential smoothing (Holt's method)
        alpha = 0.3  # level smoothing
        beta = 0.1  # trend smoothing

        level = values[0]
        trend = np.mean(np.diff(values[: min(10, len(values))]))
        if np.isnan(trend):
            trend = 0.0

        levels = [level]
        trends = [trend]
        residuals = []

        for i in range(1, len(values)):
            new_level = alpha * values[i] + (1 - alpha) * (level + trend)
            new_trend = beta * (new_level - level) + (1 - beta) * trend
            residuals.append(values[i] - (level + trend))
            level = new_level
            trend = new_trend
            levels.append(level)
            trends.append(trend)

        # Forecast mean
        forecast_mean = np.array([level + trend * (i + 1) for i in range(steps)])

        # Bootstrap confidence intervals from residuals
        residuals = np.array(residuals) if residuals else np.array([0.0])
        res_std = np.std(residuals) if len(residuals) > 1 else np.std(values) * 0.1

        # Generate CIs using expanding uncertainty
        ci_90 = []
        ci_50 = []
        for i in range(steps):
            uncertainty = res_std * np.sqrt(i + 1)
            ci_90.append(1.645 * uncertainty)  # 90% CI
            ci_50.append(0.674 * uncertainty)  # 50% CI

        ci_90 = np.array(ci_90)
        ci_50 = np.array(ci_50)

        # Build forecast points
        last_ts = pd.Timestamp(timestamps[-1])
        forecasts = []
        for i in range(steps):
            target = last_ts + timedelta(seconds=freq_seconds * (i + 1))
            mean_val = max(0, float(forecast_mean[i]))  # env values can't be negative
            forecasts.append(
                ForecastPoint(
                    target_time=target.to_pydatetime(),
                    predicted_mean=round(mean_val, 2),
                    predicted_lo90=round(max(0, mean_val - ci_90[i]), 2),
                    predicted_hi90=round(mean_val + ci_90[i], 2),
                    predicted_lo50=round(max(0, mean_val - ci_50[i]), 2),
                    predicted_hi50=round(mean_val + ci_50[i], 2),
                )
            )

        # Compute in-sample metrics
        fitted = np.array([levels[i] + trends[i] for i in range(len(levels))])
        mae = np.mean(np.abs(values - fitted))
        rmse = np.sqrt(np.mean((values - fitted) ** 2))

        return ForecastResponse(
            station_id=request.station_id,
            parameter=request.parameter,
            model_name="holt_exponential_smoothing",
            created_at=datetime.now(),
            horizon_hours=request.horizon_hours,
            forecasts=forecasts,
            model_metrics={
                "method": "double_exponential_smoothing",
                "alpha": alpha,
                "beta": beta,
                "in_sample_mae": round(float(mae), 3),
                "in_sample_rmse": round(float(rmse), 3),
                "residual_std": round(float(res_std), 3),
            },
        )

    # ==================================================================
    # PERSISTENCE FALLBACK (not enough data)
    # ==================================================================
    def _persistence_forecast(
        self, request: ForecastRequest, series: list[dict]
    ) -> ForecastResponse:
        """When < 24 data points, just repeat the last known value with wide CIs."""
        last_val = series[-1]["value"] if series else 0.0
        last_ts = series[-1]["timestamp"] if series else datetime.now()
        if not isinstance(last_ts, datetime):
            last_ts = pd.Timestamp(last_ts).to_pydatetime()

        forecasts = []
        for i in range(request.horizon_hours):
            target = last_ts + timedelta(hours=i + 1)
            uncertainty = last_val * 0.2 * (i + 1) / request.horizon_hours
            forecasts.append(
                ForecastPoint(
                    target_time=target,
                    predicted_mean=round(last_val, 2),
                    predicted_lo90=round(max(0, last_val - 1.645 * uncertainty), 2),
                    predicted_hi90=round(last_val + 1.645 * uncertainty, 2),
                    predicted_lo50=round(max(0, last_val - 0.674 * uncertainty), 2),
                    predicted_hi50=round(last_val + 0.674 * uncertainty, 2),
                )
            )

        return ForecastResponse(
            station_id=request.station_id,
            parameter=request.parameter,
            model_name="persistence_fallback",
            created_at=datetime.now(),
            horizon_hours=request.horizon_hours,
            forecasts=forecasts,
            model_metrics={"method": "persistence", "warning": "insufficient_data"},
        )


# Singleton (API key loaded from env)
forecaster = NixtlaForecaster()


# ==================================================================
# YEARLY AQI PROFILE — 12 months historical + 6 months forecast
# ==================================================================

# Indian seasonal AQI indices (relative to annual mean)
# Winter high (Dec-Jan) from inversions + crop burning;
# Summer low (Jun-Aug) from monsoon washout.
MONTHLY_SEASONAL_INDEX = {
    1: 1.30,
    2: 1.15,
    3: 0.95,
    4: 0.85,
    5: 0.80,
    6: 0.75,
    7: 0.65,
    8: 0.70,
    9: 0.80,
    10: 1.10,
    11: 1.35,
    12: 1.40,
}


def _get_aqi_category(aqi: float) -> str:
    """Map AQI value to CPCB category name."""
    if aqi <= 50:
        return "Good"
    if aqi <= 100:
        return "Satisfactory"
    if aqi <= 200:
        return "Moderate"
    if aqi <= 300:
        return "Poor"
    if aqi <= 400:
        return "Very Poor"
    return "Severe"


async def get_yearly_profile(station_id: str) -> dict:
    """
    Build a yearly AQI profile: ~12 months of historical daily averages
    from ClickHouse + 6 months of seasonal forecast.

    Returns dict with: station_id, station_name, city,
    historical[], forecast[], monthly_summary[].
    """
    client = ch_writer._get_client()

    # ── 1. Get station metadata ──────────────────────────────────────
    meta_q = f"""
        SELECT station_id, city,
               any(latitude) AS lat, any(longitude) AS lng
        FROM air_quality_raw
        WHERE station_id = '{station_id}'
        GROUP BY station_id, city
        LIMIT 1
    """
    meta_res = client.query(meta_q)
    if not meta_res.result_rows:
        return {
            "station_id": station_id,
            "station_name": station_id,
            "city": "Unknown",
            "historical": [],
            "forecast": [],
            "monthly_summary": [],
        }
    meta_row = meta_res.result_rows[0]
    city = meta_row[1]

    # ── 2. Query daily AQI averages (last ~400 days to be safe) ──────
    daily_q = f"""
        SELECT
            toDate(timestamp)   AS day,
            avg(aqi)            AS avg_aqi,
            min(aqi)            AS min_aqi,
            max(aqi)            AS max_aqi,
            count()             AS readings
        FROM air_quality_raw
        WHERE station_id = '{station_id}'
          AND aqi > 0
        GROUP BY day
        HAVING readings >= 1
        ORDER BY day ASC
    """
    daily_res = client.query(daily_q)
    daily_rows = daily_res.result_rows  # (day, avg, min, max, cnt)

    # Build historical list — keep up to last 365 days
    historical = []
    for row in daily_rows[-365:]:
        historical.append(
            {
                "date": str(row[0]),
                "avg_aqi": round(float(row[1]), 1),
                "min_aqi": round(float(row[2]), 1),
                "max_aqi": round(float(row[3]), 1),
            }
        )

    # ── Smooth historical avg_aqi with 7-day centered rolling average ──
    #    Keep raw min_aqi / max_aqi for the range band.
    if len(historical) >= 7:
        raw_avgs = [pt["avg_aqi"] for pt in historical]
        smoothed_hist = []
        for j in range(len(raw_avgs)):
            w_start = max(0, j - 3)
            w_end = min(len(raw_avgs), j + 4)  # exclusive
            smoothed_hist.append(round(float(np.mean(raw_avgs[w_start:w_end])), 1))
        for j in range(len(historical)):
            historical[j]["avg_aqi"] = smoothed_hist[j]

    # ── 3. Build lookup from ALL historical daily data ─────────────
    #    Key: (month, day) → list of avg_aqi values across years
    #    This lets us match forecast dates to same-date previous-year data.
    from collections import defaultdict
    import datetime as _dt

    # date object → avg_aqi  (for exact-date lookup)
    hist_by_date: dict[_dt.date, float] = {}
    # (month, day) → list[avg_aqi]  (for same-calendar-day lookup)
    hist_by_md: dict[tuple[int, int], list[float]] = defaultdict(list)
    # month → list[avg_aqi]  (fallback: monthly average)
    hist_by_month: dict[int, list[float]] = defaultdict(list)
    # month → list[daily_std]  (for CI estimation)
    hist_month_vals: dict[int, list[float]] = defaultdict(list)

    for row in daily_rows:
        d = row[0]  # date object
        avg_val = float(row[1])
        hist_by_date[d] = avg_val
        hist_by_md[(d.month, d.day)].append(avg_val)
        hist_by_month[d.month].append(avg_val)
        hist_month_vals[d.month].append(avg_val)

    # Annual mean AQI (used only as last-resort fallback)
    all_aqi_vals = [float(r[1]) for r in daily_rows]
    base_aqi = np.mean(all_aqi_vals) if all_aqi_vals else 150.0

    # Per-month standard deviation for CI
    month_std: dict[int, float] = {}
    for m, vals in hist_month_vals.items():
        month_std[m] = float(np.std(vals)) if len(vals) > 1 else base_aqi * 0.15

    # ── 4. Generate 6-month daily forecast using prev-year data ──────
    if historical:
        last_date = datetime.strptime(historical[-1]["date"], "%Y-%m-%d").date()
    else:
        last_date = datetime.now().date()

    forecast_points = []
    forecast_days = 180  # ~6 months

    for i in range(1, forecast_days + 1):
        fdate = last_date + timedelta(days=i)
        predicted = None

        # Priority 1: Exact date one year ago
        prev_year_date = fdate - timedelta(days=365)
        if prev_year_date in hist_by_date:
            predicted = hist_by_date[prev_year_date]

        # Priority 2: ±1-3 day window around the prev-year date
        if predicted is None:
            for offset in [1, -1, 2, -2, 3, -3]:
                nearby = prev_year_date + timedelta(days=offset)
                if nearby in hist_by_date:
                    predicted = hist_by_date[nearby]
                    break

        # Priority 3: Same calendar (month, day) from any year
        if predicted is None:
            md_vals = hist_by_md.get((fdate.month, fdate.day))
            if md_vals:
                predicted = float(np.mean(md_vals))

        # Priority 4: Monthly average + deterministic daily variation
        if predicted is None:
            m_vals = hist_by_month.get(fdate.month)
            if m_vals:
                monthly_mean = float(np.mean(m_vals))
                m_sd_fb = month_std.get(fdate.month, base_aqi * 0.15)
                noise = (
                    m_sd_fb
                    * 0.3
                    * np.sin(fdate.day * 2 * np.pi / 30 + fdate.month * 0.5)
                )
                predicted = monthly_mean + noise

        # Priority 5: Last-resort fallback (annual mean + variation)
        if predicted is None:
            noise = (
                base_aqi
                * 0.15
                * 0.3
                * np.sin(fdate.day * 2 * np.pi / 30 + fdate.month * 0.5)
            )
            predicted = base_aqi + noise

        predicted = max(10.0, round(predicted, 1))

        # Confidence interval: based on that month's actual std, widens slightly over time
        m_sd = month_std.get(fdate.month, base_aqi * 0.15)
        time_factor = 1.0 + (i / forecast_days) * 0.4  # 1.0 → 1.4 over 6 months
        ci_width = m_sd * time_factor

        forecast_points.append(
            {
                "date": str(fdate),
                "predicted": predicted,
                "lower": round(max(10.0, predicted - ci_width), 1),
                "upper": round(predicted + ci_width, 1),
            }
        )

    # ── Smooth forecast predicted with 7-day rolling average ──────────
    #    Recalculate lower/upper from the smoothed centre, keeping the
    #    original CI half-width so the band tracks the smoothed line.
    if len(forecast_points) >= 7:
        raw_preds = [pt["predicted"] for pt in forecast_points]
        smoothed_fc = []
        for j in range(len(raw_preds)):
            w_start = max(0, j - 3)
            w_end = min(len(raw_preds), j + 4)
            smoothed_fc.append(round(float(np.mean(raw_preds[w_start:w_end])), 1))
        for j in range(len(forecast_points)):
            pt = forecast_points[j]
            old_pred = pt["predicted"]
            new_pred = smoothed_fc[j]
            half_width = (pt["upper"] - pt["lower"]) / 2
            pt["predicted"] = new_pred
            pt["lower"] = round(max(10.0, new_pred - half_width), 1)
            pt["upper"] = round(new_pred + half_width, 1)

    # ── 5. Build monthly summary (historical + forecast) ─────────────
    monthly_summary = []

    # Historical months
    hist_monthly = defaultdict(list)
    for pt in historical:
        month_key = pt["date"][:7]  # "2025-04"
        hist_monthly[month_key].append(pt["avg_aqi"])
    for month_key in sorted(hist_monthly.keys()):
        avg = round(np.mean(hist_monthly[month_key]), 1)
        monthly_summary.append(
            {
                "month": month_key,
                "avg_aqi": avg,
                "category": _get_aqi_category(avg),
                "is_forecast": False,
            }
        )

    # Forecast months
    fc_monthly = defaultdict(list)
    for pt in forecast_points:
        month_key = pt["date"][:7]
        fc_monthly[month_key].append(pt["predicted"])
    for month_key in sorted(fc_monthly.keys()):
        avg = round(np.mean(fc_monthly[month_key]), 1)
        monthly_summary.append(
            {
                "month": month_key,
                "avg_aqi": avg,
                "category": _get_aqi_category(avg),
                "is_forecast": True,
            }
        )

    return {
        "station_id": station_id,
        "station_name": station_id,  # We don't have a name column; use ID
        "city": city,
        "historical": historical,
        "forecast": forecast_points,
        "monthly_summary": monthly_summary,
    }
