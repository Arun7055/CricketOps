from pydantic import BaseModel, Field, validator
from typing import List

# ==========================================
# 1. SELECTION MODULE SCHEMAS
# ==========================================

class StrategyRequest(BaseModel):
    user_xi: List[str] = Field(..., min_items=11, max_items=11, description="Your finalized Playing XI")
    opposition_xi: List[str] = Field(..., min_items=11, max_items=11, description="Opposition's Playing XI")
    venue: str
    format: str
    innings: str            # e.g., "Batting 1st", "Chasing (Batting 2nd)"
    pitch_type: str         # e.g., "Dry", "Hard", "Damp", "Green/Grass"
    weather: str            # e.g., "Overcast", "Sunny"
    wind_condition: str     # e.g., "High Wind", "Calm"
    time_of_play: str       # e.g., "Day", "Day-Night", "Night"

# --- OUTGOING JSON RESPONSE ---
class PhaseItem(BaseModel):
    phase_label: str
    tactical_script: str

class MatchupDetail(BaseModel):
    user_player: str
    opposition_player: str
    advantage: str          # e.g., "Favorable" or "Danger"
    tactical_rationale: str

class PhaseStrategy(BaseModel):
    powerplay: str
    middle_overs: str
    death_overs: str

class MatchStrategyResponse(BaseModel):
    overall_win_condition: str
    batting_phases: List[PhaseItem]  # Replaced the static 'batting_strategy'
    bowling_phases: List[PhaseItem]  # Replaced the static 'bowling_strategy'
    key_matchups: List[MatchupDetail]


# ==========================================
# 2. AUCTION MODULE SCHEMAS
# ==========================================

class TeamNeedsRequest(BaseModel):
    purse_remaining: float = Field(..., description="Total money left in Crores/Millions")
    slots_left: int = Field(..., description="Number of roster spots left to fill")
    
    # Team Need Vectors (Scale of 0.0 to 1.0 - Front-end sliders)
    need_power_hitter: float = Field(..., description="Desire for high strike rate and boundaries")
    need_anchor_batter: float = Field(..., description="Desire for high batting average and stability")
    need_wicket_taker: float = Field(..., description="Desire for low bowling strike rate")
    need_economy_bowler: float = Field(..., description="Desire for low runs conceded")

class AuctionRecommendation(BaseModel):
    player_name: str
    role: str
    impact_score: float = Field(..., description="Raw statistical power (0-100)")
    compatibility_score: float = Field(..., description="How well they fit the Team Needs (0-100%)")
    max_bid_limit: float = Field(..., description="The mathematical ceiling to bid up to")
    
class AuctionResponse(BaseModel):
    recommendations: List[AuctionRecommendation]

# ==========================================
# 4. NEWS
# ==========================================

class NewsArticle(BaseModel):
    id: str
    title: str
    summary: str
    category: str       # strictly "domestic" or "international"
    source_wire: str    # e.g., "TNPL Scout Vector", "ICC Telemetry"
    published_time: str
    impact_level: str   # "Critical", "High", or "Medium"
    tags: List[str]