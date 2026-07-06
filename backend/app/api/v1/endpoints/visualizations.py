from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import List
from pathlib import Path
import pandas as pd
import numpy as np

router = APIRouter()

# --- RESPONSE SCHEMAS ---

class DNAMetrics(BaseModel):
    batting_strike_rate: float
    batting_average: float
    boundary_percentage: float
    economy_rate: float
    bowling_strike_rate: float

class SeasonStat(BaseModel):
    year: int
    matches: int
    runs_scored: int
    strike_rate: float
    wickets: int
    economy: float
    catches: int
    stumpings:int

class PlayerLabResponse(BaseModel):
    player_name: str
    dna: DNAMetrics
    career_timeline: List[SeasonStat]

# --- DUAL-CSV READER LOGIC ---

@router.get("/player-lab/{player_name}", response_model=PlayerLabResponse)
def get_player_analytics_lab(player_name: str):
    # Navigate up 5 levels to backend root: visualizations.py -> endpoints -> v1 -> api -> app -> backend
    base_dir = Path(__file__).resolve().parents[4]
    cleaned_csv = base_dir / "cleaned_auction_profiles.csv"
    raw_csv = base_dir / "stats.csv"

    if not cleaned_csv.exists() or not raw_csv.exists():
        raise HTTPException(status_code=500, detail="Analytics data ledgers not found on server.")

    # Safe loading
    df_cleaned = pd.read_csv(cleaned_csv)
    df_raw = pd.read_csv(raw_csv)

    clean_target = player_name.strip().lower()

    # 1. FETCH STATIC CAREER DNA (From cleaned_auction_profiles)
    dna_match = df_cleaned[df_cleaned['Player_Name'].astype(str).str.strip().str.lower() == clean_target]
    
    if dna_match.empty:
        raise HTTPException(status_code=404, detail=f"No laboratory records found for '{player_name}'.")

    dna_row = dna_match.iloc[0]

    dna_payload = DNAMetrics(
        batting_strike_rate=round(float(dna_row.get('Batting_Strike_Rate', 0)), 1),
        batting_average=round(float(dna_row.get('Batting_Average', 0)), 1),
        boundary_percentage=round(float(dna_row.get('Boundary_Percentage', 0)) * 100, 1), # Send as a clean % (e.g. 18.4)
        economy_rate=round(float(dna_row.get('Economy_Rate', 0)), 2),
        bowling_strike_rate=round(float(dna_row.get('Bowling_Strike_Rate', 99.9)), 1)
    )

    # 2. FETCH MULTI-YEAR TIMELINE STREAM (From raw stats.csv, 2018-2025)
    # Ensure Year column is numeric
    df_raw['Year'] = pd.to_numeric(df_raw['Year'], errors='coerce')
    
    timeline_matches = df_raw[
        (df_raw['Player_Name'].astype(str).str.strip().str.lower() == clean_target) & 
        (df_raw['Year'] >= 2018)
    ].sort_values(by='Year', ascending=True)

    timeline_payload = []

    for _, row in timeline_matches.iterrows():
        # Calculate single-season strike rate safely
        bf = pd.to_numeric(row.get('Balls_Faced', 0), errors='coerce')
        runs = pd.to_numeric(row.get('Runs_Scored', 0), errors='coerce')
        sr = (runs / bf * 100) if (pd.notna(bf) and bf > 0) else 0.0

        # Calculate single-season economy safely
        bb = pd.to_numeric(row.get('Balls_Bowled', 0), errors='coerce')
        conceded = pd.to_numeric(row.get('Runs_Conceded', 0), errors='coerce')
        econ = (conceded / bb * 6) if (pd.notna(bb) and bb > 0) else 0.0

        # Decide 'matches played' based on whether they were active with bat or ball
        matches_played = max(
            pd.to_numeric(row.get('Matches_Batted', 0), errors='coerce'),
            pd.to_numeric(row.get('Matches_Bowled', 0), errors='coerce')
        )

        timeline_payload.append(SeasonStat(
            year=int(row['Year']),
            matches=int(pd.isna(matches_played) and 0 or matches_played),
            runs_scored=int(pd.isna(runs) and 0 or runs),
            strike_rate=round(float(sr), 1),
            wickets=int(pd.to_numeric(row.get('Wickets_Taken', 0), errors='coerce')),
            economy=round(float(econ), 2),
            catches=int(pd.to_numeric(row.get('Catches_Taken', 0), errors='coerce') or 0),
            stumpings=int(pd.to_numeric(row.get('Stumpings', 0), errors='coerce') or 0)
        ))

    return PlayerLabResponse(
        player_name=str(dna_row['Player_Name']), # Return the properly capitalized DB name!
        dna=dna_payload,
        career_timeline=timeline_payload
    )