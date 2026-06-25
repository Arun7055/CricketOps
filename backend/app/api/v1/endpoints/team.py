import json
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from groq import Groq

from app.core.config import settings
from app.core.database import get_db
from app.models.core import Player, MatchupPvP, VenueMastery
from app.schemas.core import StrategyRequest, MatchStrategyResponse

router = APIRouter()
client = Groq(api_key=settings.GROQ_API_KEY)

def normalize_venue(raw_venue: str) -> str:
    """Matches the exact normalizer from your ETL script to ensure perfect DB hits."""
    v = raw_venue.lower()
    if "chinnaswamy" in v: return "Chinnaswamy Stadium"
    if "wankhede" in v: return "Wankhede Stadium"
    if "chidambaram" in v or "chepauk" in v: return "Chepauk Stadium"
    if "eden" in v: return "Eden Gardens"
    if "narendra modi" in v or "motera" in v: return "Narendra Modi Stadium"
    if "arun jaitley" in v or "kotla" in v: return "Arun Jaitley Stadium"
    if "rajiv gandhi" in v or "uppal" in v: return "Rajiv Gandhi Stadium"
    return raw_venue.split(",")[0].strip()

# --- 1. THE STRATEGY COMPILER (POST) ---

@router.post("/war-room-strategy", response_model=MatchStrategyResponse)
def generate_match_strategy(request: StrategyRequest, db: Session = Depends(get_db)):
    
    # 1. Fetch exactly 11v11 from DB
    user_db = db.query(Player).filter(Player.name.in_(request.user_xi)).all()
    opp_db = db.query(Player).filter(Player.name.in_(request.opposition_xi)).all()
    
    if len(user_db) != 11 or len(opp_db) != 11:
        raise HTTPException(status_code=400, detail="Must provide exactly 11 valid players for both teams.")

    # Create mapping dictionaries for O(1) lookups
    user_ids = [p.id for p in user_db]
    opp_ids = [p.id for p in opp_db]
    player_map = {p.id: p.name for p in user_db + opp_db}

    # =========================================================
    # 2. THE SQL MATH ENGINE (No LLM Guessing Allowed)
    # =========================================================
    
    # A. Fetch all 1v1 Matchups between these 22 players
    all_duels = db.query(MatchupPvP).filter(
        ((MatchupPvP.batter_id.in_(user_ids)) & (MatchupPvP.bowler_id.in_(opp_ids))) |
        ((MatchupPvP.batter_id.in_(opp_ids)) & (MatchupPvP.bowler_id.in_(user_ids)))
    ).all()

    matchup_strings = []
    for duel in all_duels:
        if duel.balls_faced > 0:
            sr = round((duel.runs_scored / duel.balls_faced) * 100, 1)
            # Prevent Divide-by-Zero
            avg = round(duel.runs_scored / max(duel.dismissals, 1), 1) 
            matchup_strings.append(
                f"- {player_map[duel.batter_id]} vs {player_map[duel.bowler_id]}: {duel.runs_scored} runs in {duel.balls_faced} balls, {duel.dismissals} outs. (SR: {sr}, Avg: {avg})"
            )

    # B. Fetch all Venue Data for these 22 players
    venue_norm = normalize_venue(request.venue)
    venue_stats = db.query(VenueMastery).filter(
        VenueMastery.player_id.in_(user_ids + opp_ids),
        VenueMastery.venue_normalized == venue_norm
    ).all()

    venue_strings = []
    for v in venue_stats:
        p_name = player_map[v.player_id]
        if v.bat_balls > 0:
            sr = round((v.bat_runs / v.bat_balls) * 100, 1)
            venue_strings.append(f"- {p_name} Batting at {venue_norm}: {v.bat_runs} runs off {v.bat_balls} balls (SR: {sr}, Outs: {v.bat_dismissals})")
        if v.bowl_balls > 0:
            econ = round((v.bowl_runs_conceded / max((v.bowl_balls / 6), 1)), 1)
            venue_strings.append(f"- {p_name} Bowling at {venue_norm}: {v.bowl_wickets} wickets, Econ: {econ} ({v.bowl_balls} balls)")

    # Fallbacks if DB returns empty for this specific combination
    matchup_context = "\n".join(matchup_strings) if matchup_strings else "No historical matchups found between these specific active players."
    venue_context = "\n".join(venue_strings) if venue_strings else f"No significant historical data for these players at {venue_norm}."


    # =========================================================
    # 3. THE DEMOTED LLM PROMPT (Copywriter Mode)
    # =========================================================
    
    system_prompt = f"""
    You are a Tactical Sports Copywriter for a cricket franchise.
    Your job is to read the exact historical statistics provided below and format them into a tactical briefing.
    
    CRITICAL RULE: DO NOT INVENT OR HALLUCINATE ANY STATISTICS. You must base your matchups and strategy ONLY on the Hard Data provided below.

    ENVIRONMENTAL LOGISTICS:
    - Target Ground: {venue_norm}
    - Match Format: {request.format}
    - Innings Strategy: {request.innings}

    HARD DATA 1: VENUE MASTERY ({venue_norm})
    {venue_context}

    HARD DATA 2: 1v1 HISTORICAL MATCHUPS (IPL 2018-2025)
    {matchup_context}

    INSTRUCTIONS:
    1. Write the batting and bowling phases based on who historically performs well at this specific venue. 
    2. From the 1v1 data, identify exactly 5 Key Matchups. Label them 'Favorable' or 'Danger' for the User's team. If the user's batter has a high SR/Avg against an opp bowler, it's Favorable. If the user's batter gets dismissed often by a bowler, it's Danger. 
    3. You MUST include the exact runs, balls, or strike rates in your 'tactical_rationale'.
    4. If there is no specific data for a section, write a tactical guideline based on standard cricket logic for this format.

    Return ONLY a valid JSON object matching this exact structure:
    {{
        "overall_win_condition": "2-sentence summary based strictly on the historical data.",
        "batting_phases": [
            {{ "phase_label": "Format Phase", "tactical_script": "..." }},
            {{ "phase_label": "Format Phase", "tactical_script": "..." }},
            {{ "phase_label": "Format Phase", "tactical_script": "..." }}
        ],
        "bowling_phases": [
            {{ "phase_label": "Format Phase", "tactical_script": "..." }},
            {{ "phase_label": "Format Phase", "tactical_script": "..." }},
            {{ "phase_label": "Format Phase", "tactical_script": "..." }}
        ],
        "key_matchups": [
            {{
                "user_player": "Player Name",
                "opposition_player": "Player Name",
                "advantage": "Favorable" OR "Danger",
                "tactical_rationale": "Must include exact historical numbers from the prompt."
            }}
        ]
    }}
    """

    try:
        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                {"role": "system", "content": "You are a strict data formatter. Output strictly JSON matching the requested schema."},
                {"role": "user", "content": system_prompt}
            ],
            response_format={"type": "json_object"},
            temperature=0.1, # Dropped to 0.1 to force maximum mathematical compliance
            max_tokens=1500
        )
        return json.loads(response.choices[0].message.content)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Tactical Engine Failed: {str(e)}")


# --- 2. THE DISCOVERABLE ROSTER FEED (GET) ---

@router.get("/players")
def get_all_players(db: Session = Depends(get_db)):
    """
    Feeds the Next.js dropdowns. Sorted alphabetically for instant UX sanity.
    """
    players = db.query(Player).order_by(Player.name.asc()).all()
    return [{"id": str(p.id), "name": p.name, "role": p.role} for p in players]