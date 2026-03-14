"""
PRITHVINET Configuration Settings
"""

from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """Application settings from environment variables"""

    # Application
    APP_NAME: str = "PRITHVINET"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True

    # ClickHouse
    CLICKHOUSE_HOST: str = "localhost"
    CLICKHOUSE_PORT: int = 8123
    CLICKHOUSE_USER: str = "admin"
    CLICKHOUSE_PASSWORD: str = "prithvinet_secure_2024"
    CLICKHOUSE_DB: str = "prithvinet"

    # PostgreSQL/PostGIS
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_USER: str = "admin"
    POSTGRES_PASSWORD: str = "prithvinet_secure_2024"
    POSTGRES_DB: str = "prithvinet_geo"

    # Redis
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379

    # External APIs
    CPCB_API_URL: str = "https://app.cpcbccr.com/ccr_docs/AQI_Bulletin.json"
    OPENAQ_API_URL: str = "https://api.openaq.org/v2"
    INDIA_WRIS_URL: str = "https://indiawris.gov.in"

    # ML Models
    TIMESFM_ENABLED: bool = True
    NIXTLA_API_KEY: Optional[str] = None

    # Data.gov.in API (Real-time Air Quality from CPCB)
    DATA_GOV_API_KEY: Optional[str] = None
    DATA_GOV_RESOURCE_ID: str = "3b01bcb8-0b14-4abf-b6f2-c1bfd384ba69"

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
