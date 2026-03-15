"""
Gamification and Citizen Engagement API Endpoints
==================================================
Wired to eco_points_service for real PostgreSQL-backed
points, badges, leaderboard, and citizen reports.
"""

from fastapi import APIRouter, Query, HTTPException, Depends
from typing import Optional
from loguru import logger

from app.models.schemas import (
    AuthenticatedUser,
    CitizenReport,
    EcoPointTransaction,
    UserProfile,
    LeaderboardEntry,
    UserRole,
)
from app.services.auth import get_current_user, require_roles
from app.services.gamification.eco_points import eco_points_service, BADGE_DEFS, LEVELS

router = APIRouter()


# ------------------------------------------------------------------
# USER PROFILE
# ------------------------------------------------------------------


@router.get("/user/{user_id}", response_model=UserProfile)
async def get_user_profile(
    user_id: str,
    user: AuthenticatedUser = Depends(get_current_user),
):
    """Get citizen user profile with eco-points, level, badges, and rank."""
    if user.role == UserRole.CITIZEN and user.user_id != user_id:
        raise HTTPException(status_code=403, detail="Access denied")
    profile = await eco_points_service.get_profile(user_id)
    if not profile:
        raise HTTPException(status_code=404, detail=f"User '{user_id}' not found")
    return profile


# ------------------------------------------------------------------
# LEADERBOARD
# ------------------------------------------------------------------


@router.get("/leaderboard", response_model=list[LeaderboardEntry])
async def get_leaderboard(
    city: Optional[str] = Query(None, description="Filter by city"),
    limit: int = Query(20, ge=1, le=100, description="Number of entries"),
):
    """Get community leaderboard ranked by eco-points."""
    entries = await eco_points_service.get_leaderboard(city=city, limit=limit)
    return entries


# ------------------------------------------------------------------
# CITIZEN REPORTS
# ------------------------------------------------------------------


@router.post("/report")
async def submit_environmental_report(
    report: CitizenReport,
    user: AuthenticatedUser = Depends(get_current_user),
):
    """
    Submit a geo-tagged environmental report.
    Automatically awards eco-points based on report type and severity.
    Returns the report ID, points awarded, and any new badges earned.
    """
    try:
        if user.role != UserRole.CITIZEN:
            raise HTTPException(
                status_code=403,
                detail="Only citizen accounts can submit eco-point reports",
            )
        report.user_id = user.user_id
        result = await eco_points_service.submit_report(report)
        return result
    except Exception as e:
        logger.error(f"Failed to submit report: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to submit report: {e}")


# ------------------------------------------------------------------
# AWARD POINTS (admin / internal)
# ------------------------------------------------------------------


@router.post("/points")
async def award_eco_points(
    transaction: EcoPointTransaction,
    _: AuthenticatedUser = Depends(
        require_roles(UserRole.SUPER_ADMIN, UserRole.REGIONAL_OFFICER)
    ),
):
    """
    Award eco-points for an action (admin / internal use).
    Returns updated total, level, and any new badges.
    """
    try:
        result = await eco_points_service.award_points(transaction)
        return result
    except Exception as e:
        logger.error(f"Failed to award points: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to award points: {e}")


# ------------------------------------------------------------------
# REFERENCE DATA
# ------------------------------------------------------------------


@router.get("/badges")
async def get_badge_definitions():
    """Get all available badge definitions."""
    return {
        "badges": [
            {
                "badge_id": badge_id,
                "name": info["name"],
                "description": info["description"],
                "threshold": info["threshold"],
            }
            for badge_id, info in BADGE_DEFS.items()
        ]
    }


@router.get("/levels")
async def get_level_definitions():
    """Get all level thresholds and names."""
    return {
        "levels": [
            {"level": i + 1, "min_points": threshold, "name": name}
            for i, (threshold, name) in enumerate(LEVELS)
        ]
    }


@router.get("/")
async def get_gamification_summary():
    """Get gamification system overview."""
    return {
        "status": "active",
        "total_levels": len(LEVELS),
        "total_badges": len(BADGE_DEFS),
        "features": [
            "Environmental Reporting (air, water, noise, illegal dumping)",
            "Eco-Points Rewards with severity multipliers",
            "Community Leaderboards (city and national)",
            "Achievement Badges (9 badge types)",
            "8-tier Level System (Seedling → Biosphere Guardian)",
        ],
    }
