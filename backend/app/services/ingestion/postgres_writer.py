"""
PostgreSQL Writer — update station metadata, compliance snapshots, and gamification tables.
Uses asyncpg for async database operations.
"""

import asyncpg
from loguru import logger
from typing import Optional

from app.core.config import settings


class PostgresWriter:
    """Manages writes to PostgreSQL/PostGIS tables."""

    def __init__(self):
        self._pool: Optional[asyncpg.Pool] = None

    async def connect(self):
        """Create connection pool."""
        if self._pool is None:
            self._pool = await asyncpg.create_pool(
                host=settings.POSTGRES_HOST,
                port=int(settings.POSTGRES_PORT),
                user=settings.POSTGRES_USER,
                password=settings.POSTGRES_PASSWORD,
                database=settings.POSTGRES_DB,
                min_size=2,
                max_size=10,
            )
            logger.info("PostgreSQL connection pool created")

    async def close(self):
        if self._pool:
            await self._pool.close()
            self._pool = None

    def _ensure_pool(self):
        if self._pool is None:
            raise RuntimeError("PostgreSQL pool not initialized. Call connect() first.")

    # ------------------------------------------------------------------
    # STATION QUERIES
    # ------------------------------------------------------------------
    async def get_air_stations(
        self,
        city: Optional[str] = None,
        state: Optional[str] = None,
    ) -> list[dict]:
        self._ensure_pool()
        conditions: list[str] = []
        params: list = []
        idx = 1
        if city:
            conditions.append(f"city = ${idx}")
            params.append(city)
            idx += 1
        if state:
            conditions.append(f"state = ${idx}")
            params.append(state)
            idx += 1
        where = " AND ".join(conditions) if conditions else "TRUE"
        rows = await self._pool.fetch(
            f"""SELECT station_id, station_name, city, state, country,
                       ST_Y(geom) AS latitude, ST_X(geom) AS longitude,
                       elevation_m, station_type, operator,
                       created_at, updated_at
                FROM air_stations WHERE {where} ORDER BY state, city, station_id""",
            *params,
        )
        return [dict(r) for r in rows]

    async def get_water_stations(self, district: Optional[str] = None) -> list[dict]:
        self._ensure_pool()
        base = """SELECT station_id, station_name, station_type, water_body,
                         district, state,
                         ST_Y(geom) AS latitude, ST_X(geom) AS longitude,
                         created_at
                  FROM water_stations"""
        if district:
            rows = await self._pool.fetch(
                f"{base} WHERE district = $1 ORDER BY station_id",
                district,
            )
        else:
            rows = await self._pool.fetch(f"{base} ORDER BY station_id")
        return [dict(r) for r in rows]

    async def get_noise_stations(self, city: Optional[str] = None) -> list[dict]:
        self._ensure_pool()
        base = """SELECT station_id, station_name, zone_type, city, state,
                         ST_Y(geom) AS latitude, ST_X(geom) AS longitude,
                         day_limit, night_limit, created_at
                  FROM noise_stations"""
        if city:
            rows = await self._pool.fetch(
                f"{base} WHERE city = $1 ORDER BY station_id", city
            )
        else:
            rows = await self._pool.fetch(f"{base} ORDER BY station_id")
        return [dict(r) for r in rows]

    async def get_factories(
        self, city: Optional[str] = None, risk: Optional[str] = None
    ) -> list[dict]:
        self._ensure_pool()
        conditions = []
        params = []
        idx = 1
        if city:
            conditions.append(f"district = ${idx}")
            params.append(city)
            idx += 1
        if risk:
            conditions.append(f"industry_risk = ${idx}")
            params.append(risk)
            idx += 1

        where = " AND ".join(conditions) if conditions else "TRUE"
        rows = await self._pool.fetch(
            f"""SELECT factory_id, factory_name, industry_type, industry_risk,
                       state, district,
                       ST_Y(geom) AS latitude, ST_X(geom) AS longitude,
                       ocems_installed, last_audit_date, violation_count,
                       created_at
                FROM factories WHERE {where} ORDER BY factory_id""",
            *params,
        )
        return [dict(r) for r in rows]

    # ------------------------------------------------------------------
    # GAMIFICATION
    # ------------------------------------------------------------------
    async def get_user(self, user_id: str) -> Optional[dict]:
        self._ensure_pool()
        row = await self._pool.fetchrow(
            "SELECT * FROM users WHERE user_id = $1", user_id
        )
        return dict(row) if row else None

    async def add_eco_points(
        self, user_id: str, points: int, action: str, description: str = ""
    ) -> int:
        """Add eco points to a user. Returns new total."""
        self._ensure_pool()
        async with self._pool.acquire() as conn:
            async with conn.transaction():
                await conn.execute(
                    """INSERT INTO eco_point_transactions (user_id, points, action, description)
                       VALUES ($1, $2, $3, $4)""",
                    user_id,
                    points,
                    action,
                    description,
                )
                await conn.execute(
                    "UPDATE users SET eco_points = eco_points + $1 WHERE user_id = $2",
                    points,
                    user_id,
                )
                row = await conn.fetchrow(
                    "SELECT eco_points FROM users WHERE user_id = $1", user_id
                )
                return row["eco_points"] if row else 0

    async def get_leaderboard(
        self, city: Optional[str] = None, limit: int = 20
    ) -> list[dict]:
        self._ensure_pool()
        if city:
            rows = await self._pool.fetch(
                """SELECT user_id, username, city, eco_points, level
                   FROM users WHERE city = $1
                   ORDER BY eco_points DESC LIMIT $2""",
                city,
                limit,
            )
        else:
            rows = await self._pool.fetch(
                """SELECT user_id, username, city, eco_points, level
                   FROM users
                   ORDER BY eco_points DESC LIMIT $1""",
                limit,
            )
        return [dict(r) for r in rows]

    async def submit_citizen_report(
        self,
        report_id: str,
        user_id: str,
        report_type: str,
        lat: float,
        lon: float,
        description: str,
        severity: str = "medium",
    ) -> dict:
        self._ensure_pool()
        await self._pool.execute(
            """INSERT INTO citizen_reports
               (report_id, user_id, report_type, geom, description, severity, status)
               VALUES ($1, $2, $3, ST_SetSRID(ST_MakePoint($5, $4), 4326), $6, $7, 'pending')""",
            report_id,
            user_id,
            report_type,
            lat,
            lon,
            description,
            severity,
        )
        return {"report_id": report_id, "status": "pending"}

    async def get_user_badges(self, user_id: str) -> list[str]:
        self._ensure_pool()
        rows = await self._pool.fetch(
            "SELECT badge_id FROM user_badges WHERE user_id = $1", user_id
        )
        return [r["badge_id"] for r in rows]

    async def award_badge(self, user_id: str, badge_id: str) -> bool:
        self._ensure_pool()
        try:
            await self._pool.execute(
                """INSERT INTO user_badges (user_id, badge_id)
                   VALUES ($1, $2) ON CONFLICT DO NOTHING""",
                user_id,
                badge_id,
            )
            return True
        except Exception as e:
            logger.error(f"Failed to award badge: {e}")
            return False

    # ------------------------------------------------------------------
    # FACTORY COMPLIANCE UPDATES
    # ------------------------------------------------------------------
    async def increment_violation(self, factory_id: str) -> None:
        self._ensure_pool()
        await self._pool.execute(
            "UPDATE factories SET violation_count = violation_count + 1 WHERE factory_id = $1",
            factory_id,
        )

    # ------------------------------------------------------------------
    # HEALTH CHECK
    # ------------------------------------------------------------------
    async def health_check(self) -> bool:
        try:
            self._ensure_pool()
            row = await self._pool.fetchrow("SELECT 1 AS ok")
            return row is not None
        except Exception:
            return False


# Singleton instance
pg_writer = PostgresWriter()
