import os
import json
import glob
import sys
from sqlalchemy.orm import Session

# Import your DB engine and models
from app.core.database import SessionLocal
from app.models.core import Player, MatchupPvP, VenueMastery

def normalize_venue(raw_venue: str) -> str:
    """Squashes historical/duplicate stadium names into standard keys."""
    v = raw_venue.lower()
    if "chinnaswamy" in v: return "Chinnaswamy Stadium"
    if "wankhede" in v: return "Wankhede Stadium"
    if "chidambaram" in v or "chepauk" in v: return "Chepauk Stadium"
    if "eden" in v: return "Eden Gardens"
    if "narendra modi" in v or "motera" in v: return "Narendra Modi Stadium"
    if "arun jaitley" in v or "kotla" in v: return "Arun Jaitley Stadium"
    if "rajiv gandhi" in v or "uppal" in v: return "Rajiv Gandhi Stadium"
    
    return raw_venue.split(",")[0].strip()

def build_name_map(db: Session):
    """Creates a mapping dictionary from Cricsheet format -> Database Player ID."""
    db_players = db.query(Player).all()
    name_map = {}
    
    for p in db_players:
        name_map[p.name.lower()] = p.id
        parts = p.name.split()
        if len(parts) >= 2:
            cricsheet_style = f"{parts[0][0]} {parts[-1]}".lower()
            name_map[cricsheet_style] = p.id
            
    return name_map

def run_etl_pipeline():
    db = SessionLocal()
    print("🚀 Booting up Cricsheet ETL Pipeline...")

    # 1. Load active roster map to strictly filter data
    player_map = build_name_map(db)
    print(f"✅ Loaded {len(player_map)} player name variations from Neon DB.")

    pvp_ledger = {}
    venue_ledger = {}

    # Target the subfolder inside your data directory
    json_files = glob.glob("data/*.json")
    if not json_files:
        print("❌ Error: No JSON files found in 'data/raw_json/'. Check your paths.")
        return

    total_files = len(json_files)
    print(f"⚙️ Crunching {total_files} IPL Matches...")
    
    # 2. Loop through every match file
    for idx, file_path in enumerate(json_files, start=1):
        # Zero-dependency terminal progress update
        sys.stdout.write(f"\rParsing Match Files: [{idx}/{total_files}] Processing {os.path.basename(file_path)}")
        sys.stdout.flush()

        with open(file_path, "r", encoding="utf-8") as f:
            try:
                data = json.load(f)
            except json.JSONDecodeError:
                continue

        raw_venue = data.get("info", {}).get("venue", "Unknown Venue")
        venue = normalize_venue(raw_venue)

        innings_list = data.get("innings", [])
        for innings in innings_list:
            overs = innings.get("overs", [])
            for over in overs:
                for delivery in over.get("deliveries", []):
                    raw_batter = delivery.get("batter", "").lower()
                    raw_bowler = delivery.get("bowler", "").lower()

                    batter_id = player_map.get(raw_batter)
                    bowler_id = player_map.get(raw_bowler)

                    runs_scored = delivery.get("runs", {}).get("batter", 0)
                    is_dot = 1 if runs_scored == 0 else 0
                    
                    is_wicket = 0
                    if "wickets" in delivery:
                        for w in delivery["wickets"]:
                            if w.get("player_out", "").lower() == raw_batter and w.get("kind") != "run out":
                                is_wicket = 1

                    if batter_id and bowler_id:
                        pvp_key = (batter_id, bowler_id)
                        if pvp_key not in pvp_ledger:
                            pvp_ledger[pvp_key] = {"runs": 0, "balls": 0, "dismissals": 0, "dots": 0}
                        
                        pvp_ledger[pvp_key]["runs"] += runs_scored
                        pvp_ledger[pvp_key]["balls"] += 1
                        pvp_ledger[pvp_key]["dismissals"] += is_wicket
                        pvp_ledger[pvp_key]["dots"] += is_dot

                    if batter_id:
                        v_bat_key = (batter_id, venue)
                        if v_bat_key not in venue_ledger:
                            venue_ledger[v_bat_key] = {"bat_runs": 0, "bat_balls": 0, "bat_dismissals": 0, "bowl_balls": 0, "bowl_runs": 0, "bowl_wickets": 0}
                        
                        venue_ledger[v_bat_key]["bat_runs"] += runs_scored
                        venue_ledger[v_bat_key]["bat_balls"] += 1
                        venue_ledger[v_bat_key]["bat_dismissals"] += is_wicket

                    if bowler_id:
                        v_bowl_key = (bowler_id, venue)
                        if v_bowl_key not in venue_ledger:
                            venue_ledger[v_bowl_key] = {"bat_runs": 0, "bat_balls": 0, "bat_dismissals": 0, "bowl_balls": 0, "bowl_runs": 0, "bowl_wickets": 0}
                        
                        total_runs_conceded = delivery.get("runs", {}).get("total", 0) - delivery.get("runs", {}).get("legbyes", 0) - delivery.get("runs", {}).get("byes", 0)
                        
                        venue_ledger[v_bowl_key]["bowl_balls"] += 1
                        venue_ledger[v_bowl_key]["bowl_runs"] += total_runs_conceded
                        venue_ledger[v_bowl_key]["bowl_wickets"] += is_wicket

    print("\n\n✅ Parsing Complete! Preparing Neon DB Upload...")
    
    print("🧹 Wiping old ledger data...")
    db.query(MatchupPvP).delete()
    db.query(VenueMastery).delete()
    db.commit()

    print(f"📥 Pushing {len(pvp_ledger)} unique 1v1 matchups to Neon DB...")
    pvp_objects = [
        MatchupPvP(
            batter_id=batter,
            bowler_id=bowler,
            runs_scored=stats["runs"],
            balls_faced=stats["balls"],
            dismissals=stats["dismissals"],
            dots_faced=stats["dots"]
        )
        for (batter, bowler), stats in pvp_ledger.items()
    ]
    db.bulk_save_objects(pvp_objects)

    print(f"📥 Pushing {len(venue_ledger)} unique venue records to Neon DB...")
    venue_objects = [
        VenueMastery(
            player_id=player_id,
            venue_normalized=venue_name,
            bat_runs=stats["bat_runs"],
            bat_balls=stats["bat_balls"],
            bat_dismissals=stats["bat_dismissals"],
            bowl_balls=stats["bowl_balls"],
            bowl_runs_conceded=stats["bowl_runs"],
            bowl_wickets=stats["bowl_wickets"]
        )
        for (player_id, venue_name), stats in venue_ledger.items()
    ]
    db.bulk_save_objects(venue_objects)

    db.commit()
    db.close()
    print("🎉 ETL PIPELINE SUCCESSFUL. Your database is now lethal.")

if __name__ == "__main__":
    run_etl_pipeline()