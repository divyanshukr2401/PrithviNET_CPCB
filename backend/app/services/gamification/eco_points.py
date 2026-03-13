"""
Gamification Eco-Points Service — citizen engagement, points, badges, and leaderboard.

Point allocation:
  - Air quality report: 20 pts
  - Water quality report: 25 pts
  - Noise violation report: 15 pts
  - Green commute log: 10 pts
  - Challenge completion: varies (50-250 pts)
  - Verified report bonus: +50% of base points
  - Streak bonus: +5 pts per consecutive day (max 50)

Levels:
  Level 1: 0-99 pts     (Seedling)
  Level 2: 100-299 pts  (Sprout)
  Level 3: 300-599 pts  (Sapling)
  Level 4: 600-999 pts  (Tree)
  Level 5: 1000-1999 pts (Grove)
  Level 6: 2000-3999 pts (Forest)
  Level 7: 4000-7999 pts (Ecosystem)
  Level 8: 8000+ pts    (Biosphere Guardian)

Badges:
  first_report, air_sentinel, water_guardian, noise_patrol,
  week_streak, month_streak, top_10, community_champion
"""

from datetime import datetime
from loguru import logger
from typing import Optional
import uuid

from app.models.schemas import (
    UserProfile,
    EcoPointTransaction,
    CitizenReport,
    LeaderboardEntry,
    Severity,
)
from app.services.ingestion.postgres_writer import pg_writer


# Point allocation table
POINT_TABLE = {
    "air_report": 20,
    "water_report": 25,
    "noise_report": 15,
    "illegal_dumping_report": 30,
    "green_commute": 10,
    "tree_planting": 50,
    "awareness_share": 5,
}

# Level thresholds
LEVELS = [
    (0, "Seedling"),
    (100, "Sprout"),
    (300, "Sapling"),
    (600, "Tree"),
    (1000, "Grove"),
    (2000, "Forest"),
    (4000, "Ecosystem"),
    (8000, "Biosphere Guardian"),
]

# Badge definitions
BADGE_DEFS = {
    "first_report": {"name": "First Report", "description": "Submitted your first environmental report", "threshold": 1},
    "air_sentinel": {"name": "Air Sentinel", "description": "Submitted 10 air quality reports", "threshold": 10},
    "water_guardian": {"name": "Water Guardian", "description": "Submitted 10 water quality reports", "threshold": 10},
    "noise_patrol": {"name": "Noise Patrol", "description": "Reported 5 noise violations", "threshold": 5},
    "week_streak": {"name": "Week Warrior", "description": "7-day reporting streak", "threshold": 7},
    "month_streak": {"name": "Monthly Champion", "description": "30-day reporting streak", "threshold": 30},
    "top_10": {"name": "Top 10", "description": "Reached top 10 on city leaderboard", "threshold": 1},
    "community_champion": {"name": "Community Champion", "description": "Participated in 5 community challenges", "threshold": 5},
    "level_5": {"name": "Grove Keeper", "description": "Reached Level 5 (1000+ points)", "threshold": 1000},
}


class EcoPointsService:
    """Manages citizen gamification: points, levels, badges, reports."""

    def compute_level(self, points: int) -> tuple[int, str]:
        """Return (level_number, level_name) for a given point total."""
        level_num = 1
        level_name = "Seedling"
        for i, (threshold, name) in enumerate(LEVELS):
            if points >= threshold:
                level_num = i + 1
                level_name = name
        return level_num, level_name

    async def get_profile(self, user_id: str) -> Optional[UserProfile]:
        """Get full user profile with badges."""
        user = await pg_writer.get_user(user_id)
        if not user:
            return None

        badges = await pg_writer.get_user_badges(user_id)
        level, level_name = self.compute_level(user["eco_points"])

        # Get rank
        leaderboard = await pg_writer.get_leaderboard(limit=100)
        rank = None
        for i, entry in enumerate(leaderboard):
            if entry["user_id"] == user_id:
                rank = i + 1
                break

        return UserProfile(
            user_id=user["user_id"],
            username=user["username"],
            city=user["city"],
            eco_points=user["eco_points"],
            level=level,
            badges=badges,
            rank=rank,
        )

    async def award_points(self, transaction: EcoPointTransaction) -> dict:
        """
        Award eco-points for an action.
        Returns updated points total and any new badges earned.
        """
        # Determine base points
        base_points = POINT_TABLE.get(transaction.action, transaction.points)
        if transaction.points > 0:
            base_points = transaction.points  # allow override

        # Award points in DB
        new_total = await pg_writer.add_eco_points(
            user_id=transaction.user_id,
            points=base_points,
            action=transaction.action,
            description=transaction.description,
        )

        # Check for level up
        new_level, level_name = self.compute_level(new_total)

        # Check for new badges
        new_badges = await self._check_badges(transaction.user_id, new_total, transaction.action)

        return {
            "user_id": transaction.user_id,
            "points_awarded": base_points,
            "new_total": new_total,
            "level": new_level,
            "level_name": level_name,
            "new_badges": new_badges,
        }

    async def submit_report(self, report: CitizenReport) -> dict:
        """Submit a citizen environmental report and award points."""
        report_id = f"RPT-{uuid.uuid4().hex[:8].upper()}"

        # Save report to DB
        result = await pg_writer.submit_citizen_report(
            report_id=report_id,
            user_id=report.user_id,
            report_type=report.report_type,
            lat=report.latitude,
            lon=report.longitude,
            description=report.description,
            severity=report.severity.value,
        )

        # Determine action type for points
        action_map = {
            "air_pollution": "air_report",
            "water_pollution": "water_report",
            "noise_violation": "noise_report",
            "illegal_dumping": "illegal_dumping_report",
        }
        action = action_map.get(report.report_type, "air_report")
        base_pts = POINT_TABLE.get(action, 10)

        # Severity bonus
        severity_multiplier = {
            Severity.LOW: 1.0,
            Severity.MEDIUM: 1.2,
            Severity.HIGH: 1.5,
            Severity.CRITICAL: 2.0,
        }
        total_pts = int(base_pts * severity_multiplier.get(report.severity, 1.0))

        # Award points
        point_result = await self.award_points(EcoPointTransaction(
            user_id=report.user_id,
            points=total_pts,
            action=action,
            description=f"Report {report_id}: {report.description[:50]}",
        ))

        return {
            "report_id": report_id,
            "status": "pending",
            "points_awarded": total_pts,
            "new_total": point_result["new_total"],
            "level": point_result["level"],
            "level_name": point_result["level_name"],
            "new_badges": point_result["new_badges"],
        }

    async def get_leaderboard(
        self, city: Optional[str] = None, limit: int = 20
    ) -> list[LeaderboardEntry]:
        """Get ranked leaderboard."""
        rows = await pg_writer.get_leaderboard(city=city, limit=limit)
        entries = []
        for i, row in enumerate(rows):
            level, _ = self.compute_level(row["eco_points"])
            entries.append(LeaderboardEntry(
                rank=i + 1,
                user_id=row["user_id"],
                username=row["username"],
                city=row["city"],
                eco_points=row["eco_points"],
                level=level,
            ))
        return entries

    async def _check_badges(
        self, user_id: str, total_points: int, action: str
    ) -> list[str]:
        """Check if user has earned any new badges based on current state."""
        existing = set(await pg_writer.get_user_badges(user_id))
        new_badges = []

        # First report badge
        if "first_report" not in existing and action in POINT_TABLE:
            await pg_writer.award_badge(user_id, "first_report")
            new_badges.append("first_report")

        # Level-based badges
        if "level_5" not in existing and total_points >= 1000:
            await pg_writer.award_badge(user_id, "level_5")
            new_badges.append("level_5")

        # Top 10 badge
        leaderboard = await pg_writer.get_leaderboard(limit=10)
        if "top_10" not in existing:
            for entry in leaderboard:
                if entry["user_id"] == user_id:
                    await pg_writer.award_badge(user_id, "top_10")
                    new_badges.append("top_10")
                    break

        return new_badges


# Singleton
eco_points_service = EcoPointsService()
