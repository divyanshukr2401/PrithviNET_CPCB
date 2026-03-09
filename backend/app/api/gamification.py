"""Gamification and Citizen Engagement API Endpoints"""

from fastapi import APIRouter, Query, UploadFile, File
from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel

router = APIRouter()


class CitizenReport(BaseModel):
    """Citizen environmental report model"""
    user_id: str
    report_type: str  # noise_violation, illegal_dumping, air_quality_concern, water_pollution
    location: dict  # lat, lon
    description: str
    severity: Optional[str] = "medium"


class EcoPointTransaction(BaseModel):
    """Eco-point transaction model"""
    user_id: str
    points: int
    action: str
    description: str


@router.get("/")
async def get_gamification_summary():
    """Get gamification system summary"""
    return {
        "summary": "Citizen engagement platform active",
        "total_users": 15000,
        "active_users_30d": 3500,
        "total_reports": 25000,
        "verified_reports": 18000,
        "eco_points_distributed": 2500000,
        "features": [
            "Environmental Reporting",
            "Eco-Points Rewards",
            "Community Leaderboards",
            "Achievement Badges",
            "Local Challenges"
        ]
    }


@router.get("/user/{user_id}")
async def get_user_profile(user_id: str):
    """Get citizen user profile with gamification stats"""
    return {
        "user_id": user_id,
        "username": "eco_warrior_123",
        "level": 12,
        "eco_points": 2450,
        "rank": 156,
        "badges": [
            {"name": "First Report", "icon": "report_badge", "earned_at": "2024-01-01"},
            {"name": "Noise Guardian", "icon": "noise_badge", "earned_at": "2024-02-15"},
            {"name": "Verified 10", "icon": "verified_badge", "earned_at": "2024-03-01"}
        ],
        "statistics": {
            "total_reports": 45,
            "verified_reports": 38,
            "verification_rate": 84.4,
            "reports_this_month": 5
        },
        "impact": {
            "violations_reported": 12,
            "estimated_pollution_prevented_kg": 250
        }
    }


@router.get("/leaderboard")
async def get_leaderboard(
    scope: str = Query("city", description="Scope: city, state, national"),
    location: Optional[str] = Query(None, description="Location filter"),
    limit: int = Query(50, ge=10, le=100)
):
    """Get community leaderboard"""
    return {
        "scope": scope,
        "location": location,
        "period": "All Time",
        "leaders": [
            {"rank": 1, "user_id": "user_001", "username": "green_champion", "eco_points": 12500, "reports": 150},
            {"rank": 2, "user_id": "user_002", "username": "eco_defender", "eco_points": 11200, "reports": 132},
            {"rank": 3, "user_id": "user_003", "username": "nature_guard", "eco_points": 9800, "reports": 118}
        ],
        "total_participants": 15000,
        "updated_at": datetime.utcnow().isoformat()
    }


@router.post("/report")
async def submit_environmental_report(report: CitizenReport):
    """Submit a geo-tagged environmental report"""
    return {
        "report_id": "rpt_001",
        "status": "submitted",
        "user_id": report.user_id,
        "report_type": report.report_type,
        "location": report.location,
        "verification_status": "pending",
        "estimated_verification_time_hours": 24,
        "potential_eco_points": {
            "submission": 10,
            "if_verified": 50,
            "if_action_taken": 100
        },
        "submitted_at": datetime.utcnow().isoformat()
    }


@router.post("/report/{report_id}/media")
async def upload_report_media(
    report_id: str,
    file: UploadFile = File(...),
    media_type: str = Query("image", description="Type: image, audio, video")
):
    """Upload geo-tagged media (photo/audio) for a report"""
    return {
        "report_id": report_id,
        "media_id": "media_001",
        "media_type": media_type,
        "filename": file.filename,
        "uploaded": True,
        "bonus_eco_points": 5,
        "message": "Media attached successfully. Bonus points awarded!"
    }


@router.get("/report/{report_id}")
async def get_report_status(report_id: str):
    """Get status of a submitted report"""
    return {
        "report_id": report_id,
        "status": "verified",
        "verification_result": {
            "verified_by": "automated_ml",
            "confidence": 0.92,
            "verification_notes": "Noise violation confirmed via audio analysis"
        },
        "action_taken": {
            "status": "forwarded_to_authority",
            "authority": "Municipal Corporation",
            "ticket_id": "MCT_2024_001"
        },
        "eco_points_awarded": {
            "submission": 10,
            "verification": 50,
            "action_bonus": 100,
            "total": 160
        }
    }


@router.get("/challenges")
async def get_active_challenges(
    location: Optional[str] = Query(None, description="Location filter")
):
    """Get active community challenges"""
    return {
        "challenges": [
            {
                "challenge_id": "ch_001",
                "name": "Noise Free Week",
                "description": "Report 5 noise violations in your area",
                "type": "individual",
                "reward_eco_points": 500,
                "progress": {"current": 3, "target": 5},
                "ends_at": "2024-03-31T23:59:59Z"
            },
            {
                "challenge_id": "ch_002",
                "name": "Community Clean Air",
                "description": "Community goal: 100 verified air quality reports",
                "type": "community",
                "reward_eco_points": 200,
                "community_progress": {"current": 78, "target": 100},
                "ends_at": "2024-03-31T23:59:59Z"
            }
        ]
    }


@router.get("/rewards")
async def get_available_rewards():
    """Get rewards that can be redeemed with Eco-Points"""
    return {
        "rewards": [
            {
                "reward_id": "rew_001",
                "name": "Tree Planting Certificate",
                "description": "We plant a tree in your name",
                "eco_points_required": 500,
                "category": "environmental"
            },
            {
                "reward_id": "rew_002",
                "name": "Public Transit Pass (1 Day)",
                "description": "Free public transit pass for eco-friendly commute",
                "eco_points_required": 1000,
                "category": "transport"
            },
            {
                "reward_id": "rew_003",
                "name": "Eco Warrior Badge (Physical)",
                "description": "Limited edition physical badge",
                "eco_points_required": 5000,
                "category": "collectible"
            }
        ]
    }
