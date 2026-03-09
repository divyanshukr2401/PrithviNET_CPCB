---
name: gamification-system
description: Design and implement gamified citizen engagement with Eco-Points, leaderboards, badges, and community challenges for environmental monitoring
license: MIT
compatibility: opencode
metadata:
  domain: user-engagement
  difficulty: beginner
  patterns: gamification, rewards
---

# Gamification System for Citizen Environmental Engagement

## Overview
This skill covers the design and implementation of gamification mechanics to engage citizens in environmental monitoring. Transform passive data viewers into active environmental custodians through progression systems, rewards, and social competition.

## Why Gamification?
- Crowdsources hyperlocal data collection
- Creates decentralized verification layer
- Bridges gap between awareness and action
- Builds sustainable engagement without hardware costs
- Inspiration: TerraGenesis, environmental citizen science apps

## Core Gamification Elements

### 1. Eco-Points System
```python
from enum import Enum
from datetime import datetime, timedelta

class PointAction(Enum):
    REPORT_SUBMIT = 10
    REPORT_VERIFIED = 50
    REPORT_ACTION_TAKEN = 100
    MEDIA_ATTACHMENT = 5
    DAILY_LOGIN = 2
    CHALLENGE_COMPLETE = 200
    STREAK_BONUS_7D = 50
    STREAK_BONUS_30D = 200
    REFERRAL = 100

class EcoPointsManager:
    def __init__(self, db):
        self.db = db
    
    async def award_points(
        self,
        user_id: str,
        action: PointAction,
        description: str = None,
        multiplier: float = 1.0
    ):
        """Award Eco-Points to a user"""
        points = int(action.value * multiplier)
        
        transaction = {
            "user_id": user_id,
            "points": points,
            "action": action.value,
            "description": description or action.name,
            "timestamp": datetime.utcnow()
        }
        
        await self.db.insert("eco_point_transactions", transaction)
        await self.db.increment("users", user_id, "eco_points", points)
        
        # Check for level up
        new_total = await self.get_user_points(user_id)
        await self.check_level_up(user_id, new_total)
        
        return {"points_awarded": points, "new_total": new_total}
```

### 2. Leveling System
```python
LEVEL_THRESHOLDS = [
    (0, "Seedling"),
    (100, "Sprout"),
    (500, "Sapling"),
    (1000, "Green Warrior"),
    (2500, "Eco Guardian"),
    (5000, "Nature Defender"),
    (10000, "Earth Protector"),
    (25000, "Planet Champion"),
    (50000, "Environmental Hero"),
    (100000, "Eco Legend")
]

def calculate_level(points: int) -> dict:
    """Calculate user level from points"""
    level = 1
    title = "Seedling"
    
    for threshold, level_title in LEVEL_THRESHOLDS:
        if points >= threshold:
            level = LEVEL_THRESHOLDS.index((threshold, level_title)) + 1
            title = level_title
    
    # Calculate progress to next level
    current_idx = level - 1
    if current_idx < len(LEVEL_THRESHOLDS) - 1:
        current_threshold = LEVEL_THRESHOLDS[current_idx][0]
        next_threshold = LEVEL_THRESHOLDS[current_idx + 1][0]
        progress = (points - current_threshold) / (next_threshold - current_threshold)
    else:
        progress = 1.0
    
    return {
        "level": level,
        "title": title,
        "progress_to_next": round(progress, 2)
    }
```

### 3. Badge System
```python
BADGES = {
    "first_report": {
        "name": "First Report",
        "description": "Submit your first environmental report",
        "icon": "badge_first_report",
        "rarity": "common"
    },
    "verified_10": {
        "name": "Verified Reporter",
        "description": "Have 10 reports verified",
        "icon": "badge_verified_10",
        "rarity": "rare"
    },
    "noise_guardian": {
        "name": "Noise Guardian",
        "description": "Report 5 noise violations",
        "icon": "badge_noise",
        "rarity": "uncommon"
    },
    "water_protector": {
        "name": "Water Protector",
        "description": "Report 5 water quality issues",
        "icon": "badge_water",
        "rarity": "uncommon"
    },
    "streak_30": {
        "name": "Consistent Guardian",
        "description": "Maintain 30-day reporting streak",
        "icon": "badge_streak_30",
        "rarity": "epic"
    },
    "community_hero": {
        "name": "Community Hero",
        "description": "Reach top 10 on city leaderboard",
        "icon": "badge_hero",
        "rarity": "legendary"
    }
}

async def check_and_award_badges(user_id: str, event: str, count: int = None):
    """Check if user qualifies for new badges"""
    user_stats = await get_user_statistics(user_id)
    user_badges = await get_user_badges(user_id)
    
    new_badges = []
    
    # Check badge conditions
    if event == "report_submitted" and user_stats["total_reports"] == 1:
        if "first_report" not in user_badges:
            new_badges.append("first_report")
    
    if event == "report_verified" and user_stats["verified_reports"] >= 10:
        if "verified_10" not in user_badges:
            new_badges.append("verified_10")
    
    # Award new badges
    for badge_id in new_badges:
        await award_badge(user_id, badge_id)
    
    return new_badges
```

### 4. Leaderboard System
```python
@router.get("/leaderboard")
async def get_leaderboard(
    scope: str = "city",  # city, state, national
    location: str = None,
    period: str = "all_time",  # all_time, monthly, weekly
    limit: int = 50
):
    """Get community leaderboard"""
    
    # Build query based on scope
    query = """
        SELECT 
            user_id,
            username,
            eco_points,
            total_reports,
            verified_reports,
            RANK() OVER (ORDER BY eco_points DESC) as rank
        FROM users
        WHERE 1=1
    """
    
    if scope == "city" and location:
        query += f" AND city = '{location}'"
    elif scope == "state" and location:
        query += f" AND state = '{location}'"
    
    if period == "monthly":
        query += " AND created_at >= DATE_TRUNC('month', CURRENT_DATE)"
    elif period == "weekly":
        query += " AND created_at >= DATE_TRUNC('week', CURRENT_DATE)"
    
    query += f" ORDER BY eco_points DESC LIMIT {limit}"
    
    results = await db.execute(query)
    
    return {
        "scope": scope,
        "location": location,
        "period": period,
        "leaders": [
            {
                "rank": r["rank"],
                "user_id": r["user_id"],
                "username": r["username"],
                "eco_points": r["eco_points"],
                "reports": r["total_reports"]
            }
            for r in results
        ]
    }
```

### 5. Community Challenges
```python
from dataclasses import dataclass
from typing import List

@dataclass
class Challenge:
    challenge_id: str
    name: str
    description: str
    challenge_type: str  # individual, community
    target_action: str  # report_noise, report_air, any_report
    target_count: int
    reward_points: int
    start_date: datetime
    end_date: datetime

class ChallengeManager:
    async def create_challenge(self, challenge: Challenge):
        """Create a new community challenge"""
        await self.db.insert("challenges", challenge.__dict__)
    
    async def get_user_progress(self, user_id: str, challenge_id: str):
        """Get user's progress on a challenge"""
        challenge = await self.get_challenge(challenge_id)
        
        if challenge.challenge_type == "individual":
            # Count user's qualifying actions
            count = await self.db.count(
                "reports",
                {
                    "user_id": user_id,
                    "type": challenge.target_action,
                    "created_at": {"$gte": challenge.start_date, "$lte": challenge.end_date}
                }
            )
        else:
            # Community challenge - count all users
            count = await self.db.count(
                "reports",
                {
                    "type": challenge.target_action,
                    "created_at": {"$gte": challenge.start_date, "$lte": challenge.end_date}
                }
            )
        
        return {
            "challenge_id": challenge_id,
            "current": count,
            "target": challenge.target_count,
            "progress_percent": min(count / challenge.target_count * 100, 100),
            "completed": count >= challenge.target_count
        }
```

### 6. Citizen Reporting Flow
```python
@router.post("/report")
async def submit_environmental_report(
    user_id: str,
    report_type: str,
    location: dict,
    description: str,
    severity: str = "medium"
):
    """Submit geo-tagged environmental report"""
    
    # Create report
    report = {
        "report_id": generate_id(),
        "user_id": user_id,
        "type": report_type,
        "location": location,
        "description": description,
        "severity": severity,
        "status": "pending",
        "created_at": datetime.utcnow()
    }
    
    await db.insert("reports", report)
    
    # Award submission points
    points_result = await eco_points.award_points(
        user_id,
        PointAction.REPORT_SUBMIT,
        f"Submitted {report_type} report"
    )
    
    # Check for badges
    new_badges = await check_and_award_badges(user_id, "report_submitted")
    
    # Update challenge progress
    await challenge_manager.update_progress(user_id, report_type)
    
    return {
        "report_id": report["report_id"],
        "status": "submitted",
        "points_awarded": points_result["points_awarded"],
        "new_badges": new_badges,
        "potential_points": {
            "if_verified": PointAction.REPORT_VERIFIED.value,
            "if_action_taken": PointAction.REPORT_ACTION_TAKEN.value
        }
    }
```

## Database Schema
```sql
CREATE TABLE users (
    user_id VARCHAR PRIMARY KEY,
    username VARCHAR UNIQUE,
    email VARCHAR,
    city VARCHAR,
    state VARCHAR,
    eco_points INT DEFAULT 0,
    level INT DEFAULT 1,
    created_at TIMESTAMP
);

CREATE TABLE eco_point_transactions (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR REFERENCES users(user_id),
    points INT,
    action VARCHAR,
    description TEXT,
    timestamp TIMESTAMP
);

CREATE TABLE badges (
    user_id VARCHAR REFERENCES users(user_id),
    badge_id VARCHAR,
    earned_at TIMESTAMP,
    PRIMARY KEY (user_id, badge_id)
);

CREATE TABLE reports (
    report_id VARCHAR PRIMARY KEY,
    user_id VARCHAR REFERENCES users(user_id),
    type VARCHAR,
    location GEOMETRY(POINT, 4326),
    description TEXT,
    severity VARCHAR,
    status VARCHAR,
    verified_by VARCHAR,
    created_at TIMESTAMP
);
```

## Best Practices
1. Make early rewards easy to achieve for onboarding
2. Balance intrinsic (impact) and extrinsic (points) motivation
3. Show real-world impact of contributions
4. Create social proof through leaderboards
5. Time-limited challenges create urgency
6. Notify users of achievements immediately

## References
- Gamification in Sustainability: https://aworld.org/blog/esg/sustainability-gamification-the-key-for-a-greener-future/
- Citizen Science Gamification: https://pure.iiasa.ac.at/id/eprint/15101/1/474-2388-1-PB.pdf
