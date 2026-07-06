import uuid
from fastapi import APIRouter, HTTPException
from app.core.database import SessionLocal # Using your updated import
from app.models.core import Participant, DraftPick, Player, Lobby # <-- Added Lobby here

router = APIRouter()

@router.get("/{lobby_identifier}")
def get_lobby_teams(lobby_identifier: str):
    """
    Fetches all participants, their drafted players, and calculates 
    the 3 core auction analytics: Composition, Purse Efficiency, and Top Buys.
    """
    with SessionLocal() as db:
        # --- NEW: Smart ID Resolution ---
        try:
            # Test if the input is a valid UUID (from the auto-redirect)
            uuid_obj = uuid.UUID(lobby_identifier)
            lobby = db.query(Lobby).filter(Lobby.id == lobby_identifier).first()
        except ValueError:
            # If it fails, it's a short string like "CRK-VSI4" (from the search page)
            # Note: Change 'room_code' if your Lobby model uses a different column name for the short code
            lobby = db.query(Lobby).filter(Lobby.room_code == lobby_identifier).first()
            
        if not lobby:
            raise HTTPException(status_code=404, detail="Lobby not found")

        # Now we have the true database UUID, no matter how they searched!
        real_lobby_id = lobby.id
        # ---------------------------------

        participants = db.query(Participant).filter(Participant.lobby_id == real_lobby_id).all()
        
        if not participants:
            raise HTTPException(status_code=404, detail="No participants found for this lobby")
        
        teams = []
        for p in participants:
            picks = (
                db.query(DraftPick, Player)
                .join(Player, DraftPick.player_id == Player.id)
                .filter(DraftPick.participant_id == p.id)
                .all()
            )
            
            roster = []
            role_counts = {"BATSMAN": 0, "BOWLER": 0, "ALL-ROUNDER": 0, "WK-BATSMAN": 0}
            total_spent = 0
            
            for pick, player in picks:
                # 1. Normalize the Role String
                raw_role = str(player.role).upper()
                normalized_role = "BATSMAN"
                
                if "WICKET" in raw_role or "WK" in raw_role:
                    normalized_role = "WK-BATSMAN"
                elif "ALL" in raw_role or "ROUNDER" in raw_role:
                    normalized_role = "ALL-ROUNDER"
                elif "BOWL" in raw_role:
                    normalized_role = "BOWLER"
                elif "BAT" in raw_role:
                    normalized_role = "BATSMAN"

                role_counts[normalized_role] += 1
                total_spent += pick.sold_price
                
                roster.append({
                    "player_id": str(player.id),
                    "name": player.name,
                    "role": f"{normalized_role} ({raw_role.title()})", 
                    "base_price": player.base_price,
                    "sold_price": pick.sold_price,
                    "batting_style": getattr(player, "batting_style", "N/A"),
                    "bowling_style": getattr(player, "bowling_style", "N/A"),
                    "cricbuzz_profile": getattr(player, "cricbuzz_profile", ""),
                    "injury_status": getattr(player, "injury_profile", "Fit")
                })
            
            # Sort roster by most expensive first to easily grab top buys
            roster.sort(key=lambda x: x["sold_price"], reverse=True)
            top_buys = roster[:3] if len(roster) >= 3 else roster
            
            teams.append({
                "participant_id": str(p.id),
                "username": p.username,
                "purse_remaining": p.purse_remaining,
                "total_spent": total_spent,
                "total_players": len(roster),
                "analytics": {
                    "role_distribution": role_counts,
                    "top_buys": top_buys,
                },
                "roster": roster
            })
            
        return {
            "lobby_id": str(real_lobby_id),
            "teams": teams
        }