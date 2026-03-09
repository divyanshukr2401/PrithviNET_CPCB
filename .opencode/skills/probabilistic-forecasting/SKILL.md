---
name: probabilistic-forecasting
description: Generate time-series forecasts with confidence intervals using Google TimesFM and Nixtla StatsForecast for environmental parameters
license: MIT
compatibility: opencode
metadata:
  domain: machine-learning
  difficulty: intermediate
  frameworks: TimesFM, Nixtla, StatsForecast
---

# Probabilistic Forecasting for Environmental Monitoring

## Overview
This skill enables implementation of probabilistic time-series forecasting that generates prediction intervals rather than single point estimates. Essential for regulatory decision-making where uncertainty quantification matters.

## Why Probabilistic Forecasting?
- Regulatory decisions need confidence bounds, not just predictions
- Environmental systems are chaotic with inherent uncertainty
- Risk assessment requires knowing the range of possible outcomes
- Standard ARIMA/LSTM point forecasts are insufficient for policy

## Key Technologies

### Google TimesFM
- 200M parameter foundation model for time-series
- Pre-trained on 100 billion real-world time-points
- 16k context length for long-range dependencies
- Zero-shot forecasting without fine-tuning

### Nixtla StatsForecast
- High-performance statistical forecasting
- Native probabilistic interval generation
- Models: AutoARIMA, AutoETS, AutoTheta, MSTL
- Conformal prediction for calibrated intervals

## Implementation Patterns

### TimesFM Zero-Shot Forecasting
```python
import timesfm

# Initialize the model
tfm = timesfm.TimesFm(
    context_len=512,
    horizon_len=128,
    input_patch_len=32,
    output_patch_len=128,
    num_layers=20,
    model_dims=1280,
)
tfm.load_from_checkpoint(repo_id="google/timesfm-1.0-200m")

# Generate forecasts with confidence intervals
point_forecast, quantile_forecast = tfm.forecast(
    inputs=historical_data,
    freq=[0],  # 0 for high-frequency data
)
```

### Nixtla StatsForecast with Intervals
```python
from statsforecast import StatsForecast
from statsforecast.models import AutoARIMA, AutoETS

# Initialize with multiple models
sf = StatsForecast(
    models=[
        AutoARIMA(season_length=24),
        AutoETS(season_length=24)
    ],
    freq='H',  # Hourly data
    n_jobs=-1
)

# Fit and predict with confidence intervals
sf.fit(historical_df)
forecasts = sf.predict(
    h=24,  # 24-hour horizon
    level=[90, 95]  # 90% and 95% confidence intervals
)

# Result columns: AutoARIMA, AutoARIMA-lo-90, AutoARIMA-hi-90, etc.
```

### FastAPI Integration Pattern
```python
from fastapi import APIRouter
from typing import List

router = APIRouter()

@router.post("/forecast/air-quality")
async def forecast_air_quality(
    station_id: str,
    parameter: str,
    horizon_hours: int,
    confidence_levels: List[float] = [0.90, 0.95]
):
    # Fetch historical data from ClickHouse
    historical_data = await get_station_history(station_id, parameter)
    
    # Generate probabilistic forecast
    forecast = generate_probabilistic_forecast(
        data=historical_data,
        horizon=horizon_hours,
        levels=confidence_levels
    )
    
    return {
        "point_forecast": forecast.mean.tolist(),
        "confidence_intervals": {
            f"{int(level*100)}%": {
                "lower": forecast[f'lo-{int(level*100)}'].tolist(),
                "upper": forecast[f'hi-{int(level*100)}'].tolist()
            }
            for level in confidence_levels
        }
    }
```

## Environmental Forecasting Considerations

### Parameter-Specific Models
- **PM2.5/PM10**: High variability, use ensemble methods
- **AQI**: Composite index, forecast components separately
- **Water Quality (WQI)**: Slower dynamics, longer horizons viable
- **Noise (Lden)**: Strong temporal patterns, use MSTL

### Seasonality Handling
```python
# Multi-seasonal decomposition for environmental data
from statsforecast.models import MSTL

model = MSTL(
    season_length=[24, 168],  # Daily and weekly patterns
    trend_forecaster=AutoARIMA()
)
```

### Model Performance Metrics
- **CRPS** (Continuous Ranked Probability Score): Primary metric for probabilistic forecasts
- **Coverage**: Percentage of actuals within confidence intervals
- **Interval Width**: Narrower is better if coverage maintained

## Best Practices
1. Use at least 2-3 weeks of hourly data for training
2. Always validate coverage rates on holdout data
3. Account for seasonal patterns (daily, weekly, annual)
4. Use ensemble of models for robust predictions
5. Cache model artifacts for fast inference during demos

## References
- TimesFM: https://github.com/google-research/timesfm
- Nixtla StatsForecast: https://nixtlaverse.nixtla.io/statsforecast/
- Probabilistic Forecasting Tutorial: https://nixtlaverse.nixtla.io/statsforecast/docs/tutorials/uncertaintyintervals.html
