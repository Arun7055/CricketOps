import json
import asyncio
import aio_pika
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Dict, List

from app.core.config import settings
from app.core.database import get_db, SessionLocal
from app.models.core import Lobby, Player, DraftPick, Participant, DraftPick

lobby_timers: Dict[str, asyncio.Task] = {}
lobby_skip_votes: dict[str, set] = {}

router = APIRouter()

# ==========================================
# 1. THE WEBSOCKET MANAGER (IN-MEMORY STATE)
# ==========================================
class ConnectionManager:
    def __init__(self):
        # Maps lobby_id to a list of active WebSocket connections
        self.active_connections: Dict[str, List[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, lobby_id: str):
        await websocket.accept()
        if lobby_id not in self.active_connections:
            self.active_connections[lobby_id] = []
        self.active_connections[lobby_id].append(websocket)

    def disconnect(self, websocket: WebSocket, lobby_id: str):
        if lobby_id in self.active_connections:
            self.active_connections[lobby_id].remove(websocket)
            if not self.active_connections[lobby_id]:
                del self.active_connections[lobby_id]

    async def broadcast_to_lobby(self, lobby_id: str, message: dict):
        """Pushes a JSON update to every friend in the specific room."""
        if lobby_id in self.active_connections:
            for connection in self.active_connections[lobby_id]:
                try:
                    await connection.send_json(message)
                except Exception:
                    pass

manager = ConnectionManager()

# ==========================================
# 2. THE RABBITMQ PRODUCER (THE BID CATCHER)
# ==========================================
async def publish_bid_to_queue(lobby_id: str, participant_id: str, bid_amount: int):
    """Fires the bid into CloudAMQP instantly instead of locking the database."""
    try:
        connection = await aio_pika.connect_robust(settings.RABBITMQ_URL)
        async with connection:
            channel = await connection.channel()
            # Ensure the queue exists
            queue = await channel.declare_queue("live_bids_queue", durable=True)
            
            payload = {
                "lobby_id": lobby_id,
                "participant_id": participant_id,
                "bid_amount": bid_amount
            }
            
            await channel.default_exchange.publish(
                aio_pika.Message(
                    body=json.dumps(payload).encode(),
                    delivery_mode=aio_pika.DeliveryMode.PERSISTENT
                ),
                routing_key="live_bids_queue"
            )
    except Exception as e:
        print(f"RabbitMQ Error: {e}")


# ==========================================
# 3. WEBSOCKET ENDPOINT (FRONTEND CONNECTION)
# ==========================================
@router.websocket("/ws/{lobby_id}/{participant_id}")
async def auction_endpoint(websocket: WebSocket, lobby_id: str, participant_id: str):
    await manager.connect(websocket, lobby_id)
    try:
        while True:
            # 1. Receive the raw message from Next.js
            raw_data = await websocket.receive_text()
            
            # 2. Parse the JSON
            parsed_data = json.loads(raw_data)
            
            # 3. Safely extract the 'action' variable (GUARANTEES it is defined)
            action = parsed_data.get("action")
            
            # 4. Route the action
            if action == "PLACE_BID":
                # Throw it in the queue for the worker to handle
                await publish_bid_to_queue(lobby_id, participant_id, parsed_data.get("amount", 0))
                
            elif action == "FORCE_SELL_VOTE":
                print(f"📩 Vote received from {participant_id}")
                if lobby_id not in lobby_skip_votes:
                    lobby_skip_votes[lobby_id] = set()
                    
                lobby_skip_votes[lobby_id].add(participant_id)
                
                db = SessionLocal()
                try:
                    total_players = db.query(Participant).filter(Participant.lobby_id == lobby_id).count()
                finally:
                    db.close()
                    
                current_votes = len(lobby_skip_votes[lobby_id])
                print(f"🗳️ {current_votes}/{total_players} have voted to skip.")
                
                await manager.broadcast_to_lobby(lobby_id, {
                    "type": "VOTE_UPDATE",
                    "current": current_votes,
                    "required": total_players
                })
                
                # If everyone agrees, force the sale instantly
                if current_votes >= total_players and total_players > 0:
                    print("🚀 CONSENSUS! Forcing instant sale.")
                    lobby_skip_votes[lobby_id].clear()
                    if lobby_id in lobby_timers:
                        lobby_timers[lobby_id].cancel()
                    
                    await finalize_auction(lobby_id, immediate=True)

            elif action == "FINISH_AUCTION_CHECK":
                db = SessionLocal()
                try:
                    participants = db.query(Participant).filter(Participant.lobby_id == lobby_id).all()
                    
                    # Check actual draft counts for everyone
                    short_players = []
                    for p in participants:
                        pick_count = db.query(DraftPick).filter(DraftPick.participant_id == p.id).count()
                        if pick_count < 12:
                            short_players.append(p.username)
                    
                    if not short_players: # If the short_players list is empty, everyone has 12!
                        # Mark lobby as completed
                        lobby = db.query(Lobby).filter(Lobby.id == lobby_id).first()
                        if lobby:
                            lobby.status = "completed"
                            db.commit()
                        
                        # Tell everyone to redirect!
                        await manager.broadcast_to_lobby(lobby_id, {
                            "type": "AUCTION_COMPLETED",
                            "message": "All teams have 12 players! Redirecting to Analysis..."
                        })
                    else:
                        # Warn the room if people are short
                        await manager.broadcast_to_lobby(lobby_id, {
                            "type": "SYSTEM_MESSAGE",
                            "message": f"⚠️ Cannot end yet. Still need players: {', '.join(short_players)}"
                        })
                finally:
                    db.close()
                    
    except WebSocketDisconnect:
        manager.disconnect(websocket, lobby_id)

# ==========================================
# 4. LOBBY STATE API (Fetches the active player)
# ==========================================
@router.get("/state/{lobby_id}")
def get_auction_state(lobby_id: str, db: Session = Depends(get_db)):
    lobby = db.query(Lobby).filter(Lobby.id == lobby_id).first()
    if not lobby:
        raise HTTPException(status_code=404, detail="Lobby not found")

    # If no player is currently on the block, grab the next available player
    if not lobby.current_player_id:
        # Subquery: Get all player IDs already drafted in this specific lobby
        drafted_subquery = db.query(DraftPick.player_id).filter(DraftPick.lobby_id == lobby.id)
        
        # Query: Find the first player NOT in that drafted list
        next_player = db.query(Player).filter(~Player.id.in_(drafted_subquery)).first()

        if not next_player:
            return {"status": "completed", "message": "All players sold!"}

        lobby.current_player_id = next_player.id
        lobby.current_bid = next_player.base_price or 50 # Default to 50L if null
        db.commit()
        db.refresh(lobby)

    # Fetch the details of whoever is currently on the block
    active_player = db.query(Player).filter(Player.id == lobby.current_player_id).first()
    
    highest_bidder_name = "None"
    if lobby.highest_bidder_id:
        bidder = db.query(Participant).filter(Participant.id == lobby.highest_bidder_id).first()
        if bidder:
            highest_bidder_name = bidder.username

    return {
        "status": lobby.status,
        "player": {
            "id": str(active_player.id),
            "name": active_player.name,
            "role": active_player.role or "Unknown",
            "base_price": active_player.base_price or 50
        },
        "current_bid": lobby.current_bid,
        "highest_bidder_name": highest_bidder_name
    }

# ==========================================
# 5. THE RABBITMQ CONSUMER (THE BRAIN)
# ==========================================
async def consume_bids():
    """Constantly listens to the queue, validates DB, and broadcasts updates."""
    try:
        connection = await aio_pika.connect_robust(settings.RABBITMQ_URL)
        channel = await connection.channel()
        queue = await channel.declare_queue("live_bids_queue", durable=True)
        
        print("🐰 RabbitMQ Consumer is online and listening for live bids...")
        
        async with queue.iterator() as queue_iter:
            async for message in queue_iter:
                async with message.process():
                    data = json.loads(message.body.decode())
                    lobby_id = data.get("lobby_id")
                    participant_id = data.get("participant_id")
                    bid_amount = data.get("bid_amount")
                    
                    # 1. Validate against the PostgreSQL Database
                    with SessionLocal() as db:
                        lobby = db.query(Lobby).filter(Lobby.id == lobby_id).first()
                        
                        # Only accept the bid if it's strictly higher than the current price
                        if lobby and lobby.current_player_id and bid_amount > lobby.current_bid:
                            lobby.current_bid = bid_amount
                            lobby.highest_bidder_id = participant_id
                            db.commit()
                            
                            # 2. Find out who actually placed the bid
                            bidder = db.query(Participant).filter(Participant.id == participant_id).first()
                            bidder_name = bidder.username if bidder else "Unknown"
                            
                            # 3. Broadcast the victory instantly to all connected friends!
                            await manager.broadcast_to_lobby(lobby_id, {
                                "type": "AUCTION_UPDATE",
                                "current_bid": bid_amount,
                                "highest_bidder_name": bidder_name
                            })
                            
                            # --- FIXED LOGIC START ---
                            
                            # 4. Clear skip votes since a new valid bid was placed
                            if lobby_id in lobby_skip_votes:
                                lobby_skip_votes[lobby_id].clear()

                            # 5. Cancel the old timer if it exists
                            if lobby_id in lobby_timers:
                                lobby_timers[lobby_id].cancel()
                                
                            # 6. ALWAYS start a fresh 15-second timer for a successful bid!
                            print(f"⏱️ Valid bid of {bid_amount}L! Starting 15s timer for {lobby_id}...")
                            lobby_timers[lobby_id] = asyncio.create_task(finalize_auction(lobby_id))
                            
                            # --- FIXED LOGIC END ---

    except Exception as e:
        print(f"🚨 RabbitMQ Consumer Error: {e}")

# ==========================================
# 6 THE SOLD TIMER FUNCTION
# ==========================================
async def finalize_auction(lobby_id: str, immediate: bool = False):
    print(f"▶️ [START] Finalize Triggered for {lobby_id}. Immediate? {immediate}")
    try:
        if not immediate:
            await asyncio.sleep(15)
            
        print(f"⏳ [WAKE UP] Timer finished for {lobby_id}. Connecting to DB...")
        
        # Using strict try/finally to ensure DB lock is released
        db = SessionLocal()
        try:
            lobby = db.query(Lobby).filter(Lobby.id == lobby_id).first()
            if not lobby:
                print("🛑 [EARLY RETURN] Lobby not found in DB!")
                return
            if not lobby.current_player_id:
                print("🛑 [EARLY RETURN] No active player on the block!")
                return

            # SCENARIO A: No one bid
            if not lobby.highest_bidder_id:
                print("⚠️ [UNSOLD] No highest bidder. Marking as unsold.")
                
                # --- NEW: Save as unsold so they don't appear again! ---
                unsold_pick = DraftPick(
                    lobby_id=lobby.id,
                    participant_id=None, # Nobody bought them
                    player_id=lobby.current_player_id,
                    sold_price=0
                )
                db.add(unsold_pick)
                # --------------------------------------------------------

                lobby.current_player_id = None
                lobby.current_bid = 0
                db.commit()
                
                await manager.broadcast_to_lobby(lobby_id, {
                    "type": "PLAYER_SOLD",
                    "buyer": "None",
                    "amount": 0,
                    "message": "❌ UNSOLD! The room passed on this player."
                })
                return
            
            # SCENARIO B: Player is Sold
            print(f"✅ [SELLING] Found highest bidder: {lobby.highest_bidder_id} for {lobby.current_bid}L")
            winning_amount = lobby.current_bid
            highest_bidder_id = lobby.highest_bidder_id
            player_id = lobby.current_player_id

            # 1. Update Purse Safely
            bidder = db.query(Participant).filter(Participant.id == highest_bidder_id).first()
            winner_name = bidder.username if bidder else "Unknown"
            if bidder:
                bidder.purse_remaining -= winning_amount
                if bidder.squad_size is None:
                    bidder.squad_size = 0
                bidder.squad_size += 1
                
            # 2. Add the Draft Pick
            pick = DraftPick(
                lobby_id=lobby.id,
                participant_id=highest_bidder_id,
                player_id=player_id,
                sold_price=winning_amount
            )
            db.add(pick)

            # 3. Clear the block
            lobby.current_player_id = None
            lobby.current_bid = 0
            lobby.highest_bidder_id = None
            
            db.commit()
            print(f"💾 [SAVED] Successfully saved Draft Pick for {winner_name}!")

        finally:
            db.close() # FORCES the database to unlock so the next fetch works

        # 4. Broadcast the successful sale
        print("📡 [BROADCAST] Telling frontend to update...")
        await manager.broadcast_to_lobby(lobby_id, {
            "type": "PLAYER_SOLD",
            "buyer": winner_name,
            "amount": winning_amount,
            "message": f"🔨 SOLD! Player goes to {winner_name} for ₹{winning_amount}L!"
        })

    except asyncio.CancelledError:
        print("⏹️ [CANCELLED] Timer reset because a new bid came in!")
    except Exception as e:
        print(f"🚨 [FATAL ERROR] {e}")

# ==========================================
# 7.GET PARTICIPANT PURSE AND SIZE
# ==========================================
@router.get("/participant/{participant_id}/purse")
def get_participant_purse(participant_id: str):
    """Fetches the real-time purse balance and squad size from the DB."""
    with SessionLocal() as db:
        participant = db.query(Participant).filter(Participant.id == participant_id).first()
        if not participant:
            raise HTTPException(status_code=404, detail="Participant not found")
            
        # --- NEW: Dynamically count the actual draft picks! ---
        actual_squad_size = db.query(DraftPick).filter(DraftPick.participant_id == participant_id).count()
        
        return {
            "purse_remaining": participant.purse_remaining,
            "squad_size": actual_squad_size
        }