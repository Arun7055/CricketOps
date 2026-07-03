import random
import string
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from app.core.database import get_db
from app.models.core import Lobby, Participant

router = APIRouter()

# --- Pydantic Request Models ---
class CreateLobbyRequest(BaseModel):
    username: str

class JoinLobbyRequest(BaseModel):
    room_code: str
    username: str

def generate_room_code() -> str:
    """Generates a clean, readable 6-character room code like CRK-A8F"""
    chars = string.ascii_uppercase + string.digits
    return f"CRK-{''.join(random.choices(chars, k=4))}"

# ==========================================
# 1. CREATE LOBBY ENDPOINT (The Host clicks this)
# ==========================================
@router.post("/create")
def create_party_lobby(request: CreateLobbyRequest, db: Session = Depends(get_db)):
    if not request.username.strip():
        raise HTTPException(status_code=400, detail="Nickname cannot be empty.")

    # Generate a unique code that isn't currently active
    code = generate_room_code()
    while db.query(Lobby).filter(Lobby.room_code == code, Lobby.status != "completed").first():
        code = generate_room_code()

    # 1. Initialize the new room
    new_lobby = Lobby(
        room_code=code,
        status="waiting",
        current_bid=0
    )
    db.add(new_lobby)
    db.flush() # Flushes to get the new_lobby.id UUID generated

    # 2. Add the host as Participant #1
    host = Participant(
        lobby_id=new_lobby.id,
        username=request.username.strip(),
        purse_remaining=10000, # 100 Crores (represented as 10,000 Lakhs)
        squad_size=0
    )
    db.add(host)
    db.commit()

    return {
        "room_code": new_lobby.room_code,
        "lobby_id": str(new_lobby.id),
        "participant_id": str(host.id),
        "username": host.username
    }

# ==========================================
# 2. JOIN LOBBY ENDPOINT (Friends click this)
# ==========================================
@router.post("/join")
def join_party_lobby(request: JoinLobbyRequest, db: Session = Depends(get_db)):
    # Find the active room matching the code
    lobby = db.query(Lobby).filter(Lobby.room_code == request.room_code.upper(), Lobby.status == "waiting").first()
    if not lobby:
        raise HTTPException(status_code=404, detail="Room code not found or game already started.")

    # Prevent duplicate usernames within the same room to avoid chaos
    existing = db.query(Participant).filter(Participant.lobby_id == lobby.id, Participant.username == request.username.strip()).first()
    if existing:
        raise HTTPException(status_code=400, detail="That nickname is already taken in this room.")

    # Add the friend to the room
    new_player = Participant(
        lobby_id=lobby.id,
        username=request.username.strip(),
        purse_remaining=10000,
        squad_size=0
    )
    db.add(new_player)
    db.commit()

    return {
        "room_code": lobby.room_code,
        "lobby_id": str(lobby.id),
        "participant_id": str(new_player.id),
        "username": new_player.username
    }