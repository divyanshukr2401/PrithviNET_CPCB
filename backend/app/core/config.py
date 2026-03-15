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
    DATA_GOV_API_KEY: str = "579b464db66ec23bdd000001bc6f0074ab864acb60a45cfbeb72efdd"

    # ML Models
    TIMESFM_ENABLED: bool = True
    NIXTLA_API_KEY: Optional[str] = None

    # Gemini AI (Copilot)
    GEMINI_API_KEY: Optional[str] = None

    # Application auth
    APP_AUTH_SECRET: str = "prithvinet_app_auth_secret_2026"
    AUTH_TOKEN_EXPIRE_HOURS: int = 12

    # OCEMS Alerts workbook sources
    OCEMS_INDUSTRY_WORKBOOK: str = (
        r"D:\Downloads\Industry_details_COMPLETE_WITH_CONTACTS.xlsx"
    )
    OCEMS_STANDARDS_WORKBOOK: str = (
        r"D:\Downloads\India_Pollution_Standards_AIR_WATER_NOISE (1).xlsx"
    )

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
