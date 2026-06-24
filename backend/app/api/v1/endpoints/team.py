import json
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from groq import Groq

from app.core.config import settings
from app.core.database import get_db
from app.models.core import Player
from app.schemas.core import StrategyRequest, MatchStrategyResponse

router = APIRouter()
client = Groq(api_key=settings.GROQ_API_KEY)

@router.post("/war-room-strategy", response_model=MatchStrategyResponse)
def generate_match_strategy(request: StrategyRequest, db: Session = Depends(get_db)):
    
    user_db = db.query(Player).filter(Player.name.in_(request.user_xi)).all()
    opp_db = db.query(Player).filter(Player.name.in_(request.opposition_xi)).all()
    
    if len(user_db) != 11 or len(opp_db) != 11:
        raise HTTPException(status_code=400, detail="Must provide exactly 11 valid players for both teams.")

    def format_player_data(players):
        return "\n".join([
            f"- {p.name} | Role: {p.role} | Batting: {p.batting_style} | Bowling: {p.bowling_style}"
            for p in players
        ])

    system_prompt = f"""
    You are the elite Grandmaster Tactician of a professional cricket franchise.
    Analyze this 11 vs 11 matchup and generate a highly specific, format-accurate tactical blueprint.

    ENVIRONMENTAL CONDITIONS:
    - Match Format: {request.format}
    - Ground/Pitch: {request.venue} ({request.pitch_type})
    - Innings: {request.innings}
    - Atmosphere: {request.weather}, {request.time_of_play}

    YOUR PLAYING XI:
    {format_player_data(user_db)}

    OPPOSITION PLAYING XI:
    {format_player_data(opp_db)}

    FORMAT-SPECIFIC PHASIC LAW:
    You must return exactly 3 chronological phase objects for Batting, and 3 for Bowling. The 'phase_label' must strictly adapt to the selected Match Format ({request.format}):
    
    - If format is 'T20' or 'T10': Use "Powerplay (Overs 1-6)", "Middle Overs (7-15)", "Death Overs (16-20)".
    - If format is 'ODI': Use "Powerplay 1 (Overs 1-10)", "Middle Ring (11-40)", "Death Surge (41-50)".
    - If format is 'Test': STRICTLY FORBIDDEN from using the word 'Powerplay' or 'Death overs'. You MUST use red-ball phases: "Session 1: The New Ball (Overs 1-25)", "The Old Ball Grind (Overs 26-80)", and "The Second New Ball (Overs 81+)".

    Return ONLY a valid JSON object matching this exact structure:
    {{
        "overall_win_condition": "2-sentence masterclass summary of the core win factor.",
        "batting_phases": [
            {{ "phase_label": "Format-Correct Name", "tactical_script": "Actionable instructions..." }},
            {{ "phase_label": "Format-Correct Name", "tactical_script": "Actionable instructions..." }},
            {{ "phase_label": "Format-Correct Name", "tactical_script": "Actionable instructions..." }}
        ],
        "bowling_phases": [
            {{ "phase_label": "Format-Correct Name", "tactical_script": "Actionable instructions..." }},
            {{ "phase_label": "Format-Correct Name", "tactical_script": "Actionable instructions..." }},
            {{ "phase_label": "Format-Correct Name", "tactical_script": "Actionable instructions..." }}
        ],
        "key_matchups": [
            {{
                "user_player": "Your Player Name",
                "opposition_player": "Opponent Name",
                "advantage": "Favorable" OR "Danger",
                "tactical_rationale": "1-sentence tactical breakdown..."
            }}
        ]
    }}
    """

    try:
        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                {"role": "system", "content": "You are a tactical JSON compiler. Output strictly JSON matching the requested schema."},
                {"role": "user", "content": system_prompt}
            ],
            response_format={"type": "json_object"},
            temperature=0.2, 
            max_tokens=1500
        )
        return json.loads(response.choices[0].message.content)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Tactical Engine Failed: {str(e)}")
    
@router.get("/players")
def get_all_players(db: Session = Depends(get_db)):
    """
    Feeds the Next.js dropdowns. Sorted alphabetically for instant UX sanity.
    """
    players = db.query(Player).order_by(Player.name.asc()).all()
    return [{"id": str(p.id), "name": p.name, "role": p.role} for p in players]