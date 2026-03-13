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
                freq = "5min"   # Air quality: 5-min intervals
            elif median_gap < timedelta(hours=2):
                freq = "1h"     # Water: hourly
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
            forecasts.append(ForecastPoint(
                target_time=row["ds"],
                predicted_mean=float(row.get("TimeGPT", row.iloc[1])),
                predicted_lo90=float(row.get("TimeGPT-lo-90", row.iloc[1] * 0.7)),
                predicted_hi90=float(row.get("TimeGPT-hi-90", row.iloc[1] * 1.3)),
                predicted_lo50=float(row.get("TimeGPT-lo-50", row.iloc[1] * 0.85)),
                predicted_hi50=float(row.get("TimeGPT-hi-50", row.iloc[1] * 1.15)),
            ))

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
            median_gap = np.median(np.diff(timestamps.astype(np.int64))) / 1e9  # seconds
            freq_seconds = max(300, int(median_gap))  # minimum 5 min
        else:
            freq_seconds = 3600

        steps = (request.horizon_hours * 3600) // freq_seconds

        # Double exponential smoothing (Holt's method)
        alpha = 0.3  # level smoothing
        beta = 0.1   # trend smoothing

        level = values[0]
        trend = np.mean(np.diff(values[:min(10, len(values))]))
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
            forecasts.append(ForecastPoint(
                target_time=target.to_pydatetime(),
                predicted_mean=round(mean_val, 2),
                predicted_lo90=round(max(0, mean_val - ci_90[i]), 2),
                predicted_hi90=round(mean_val + ci_90[i], 2),
                predicted_lo50=round(max(0, mean_val - ci_50[i]), 2),
                predicted_hi50=round(mean_val + ci_50[i], 2),
            ))

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
            forecasts.append(ForecastPoint(
                target_time=target,
                predicted_mean=round(last_val, 2),
                predicted_lo90=round(max(0, last_val - 1.645 * uncertainty), 2),
                predicted_hi90=round(last_val + 1.645 * uncertainty, 2),
                predicted_lo50=round(max(0, last_val - 0.674 * uncertainty), 2),
                predicted_hi50=round(last_val + 0.674 * uncertainty, 2),
            ))

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
