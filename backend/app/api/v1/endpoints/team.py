from fastapi import APIRouter, HTTPException
from app.core.database import get_db, SessionLocal
from app.models.core import Participant, DraftPick, Player

router = APIRouter()

@router.get("/{lobby_id}")
def get_lobby_teams(lobby_id: str):
    """
    Fetches all participants, their drafted players, and calculates 
    the 3 core auction analytics: Composition, Purse Efficiency, and Top Buys.
    """
    with SessionLocal() as db:
        participants = db.query(Participant).filter(Participant.lobby_id == lobby_id).all()
        
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
            role_counts = {"Batter": 0, "Bowler": 0, "All-Rounder": 0, "Wicket-Keeper": 0}
            total_spent = 0
            
            for pick, player in picks:
                # 1. Track Roles for Composition
                # (Adjust these string keys based on exactly how roles are spelled in your database)
                if player.role in role_counts:
                    role_counts[player.role] += 1
                else:
                    role_counts[player.role] = 1 # Catch-all for other roles
                    
                total_spent += pick.sold_price
                
                roster.append({
                    "player_id": str(player.id),
                    "name": player.name,
                    "role": player.role,
                    "base_price": player.base_price,
                    "sold_price": pick.sold_price
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
            "lobby_id": lobby_id,
            "teams": teams
        }