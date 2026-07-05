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
# 3. THE LIVE WEBSOCKET ROUTE
# ==========================================
@router.websocket("/ws/{lobby_id}/{participant_id}")
async def auction_endpoint(websocket: WebSocket, lobby_id: str, participant_id: str):
    """
    The frontend connects here. It stays open forever until the user leaves.
    """
    await manager.connect(websocket, lobby_id)
    
    try:
        # Tell everyone in the room that a new friend joined
        await manager.broadcast_to_lobby(lobby_id, {
            "type": "SYSTEM_MESSAGE",
            "message": f"Participant {participant_id} joined the war room."
        })

        # Listen for bids from this specific user's browser
        while True:
            data = await websocket.receive_json()
            
            if data.get("action") == "PLACE_BID":
                bid_amount = data.get("amount")
                # Immediately offload the bid to the Queue to prevent race conditions
                await asyncio.create_task(publish_bid_to_queue(lobby_id, participant_id, bid_amount))
                
    except WebSocketDisconnect:
        manager.disconnect(websocket, lobby_id)
        await manager.broadcast_to_lobby(lobby_id, {
            "type": "SYSTEM_MESSAGE",
            "message": f"Participant {participant_id} disconnected."
        })

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
# 2.5 THE RABBITMQ CONSUMER (THE BRAIN)
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
                        if lobby and bid_amount > lobby.current_bid:
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
                            if lobby_id in lobby_timers:
                                lobby_timers[lobby_id].cancel()
                                lobby_timers[lobby_id] = asyncio.create_task(finalize_auction(lobby_id))

                        if lobby_id in lobby_skip_votes:
                                lobby_skip_votes[lobby_id].clear()

    except Exception as e:
        print(f"RabbitMQ Consumer Error: {e}")

# ==========================================
# 2.6 THE SOLD TIMER FUNCTION
# ==========================================
async def finalize_auction(lobby_id: str):
    """Waits 15 seconds. If not cancelled by a new bid, sells the player."""
    try:
        await asyncio.sleep(15)
        
        # If we wake up after 15s without being cancelled, the hammer drops!
        with SessionLocal() as db:
            lobby = db.query(Lobby).filter(Lobby.id == lobby_id).first()
            if not lobby or not lobby.current_player_id:
                return
            
            if not lobby.highest_bidder_id:
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
            
            elif action == "FORCE_SELL_VOTE":
                if lobby_id not in lobby_skip_votes:
                    lobby_skip_votes[lobby_id] = set()
                    
                lobby_skip_votes[lobby_id].add(participant_id)
                
                # Check how many players are in this room
                with SessionLocal() as db:
                    total_players = db.query(Participant).filter(Participant.lobby_id == lobby_id).count()
                    
                current_votes = len(lobby_skip_votes[lobby_id])
                
                # Tell the UI to update the vote counter
                await manager.broadcast_to_lobby(lobby_id, {
                    "type": "VOTE_UPDATE",
                    "current": current_votes,
                    "required": total_players
                })
            
            if current_votes >= total_players and total_players > 0:
                    lobby_skip_votes[lobby_id].clear()
                    if lobby_id in lobby_timers:
                        lobby_timers[lobby_id].cancel()
                    
                    await finalize_auction(lobby_id)

            # 1. Create the Draft Pick
            pick = DraftPick(
                lobby_id=lobby.id,
                participant_id=lobby.highest_bidder_id,
                player_id=lobby.current_player_id,
                winning_bid=lobby.current_bid
            )
            db.add(pick)

            # 2. Deduct money from the winner
            bidder = db.query(Participant).filter(Participant.id == lobby.highest_bidder_id).first()
            if bidder:
                bidder.purse_remaining -= lobby.current_bid
                bidder.squad_size += 1
                winner_name = bidder.username
            else:
                winner_name = "Unknown"

            # 3. Clear the block for the next player
            lobby.current_player_id = None
            lobby.current_bid = 0
            lobby.highest_bidder_id = None
            db.commit()

            # 4. Broadcast the Sold Event to all friends
            await manager.broadcast_to_lobby(lobby_id, {
                "type": "PLAYER_SOLD",
                "buyer": winner_name,
                "amount": pick.winning_bid,
                "message": f"🔨 SOLD! Player goes to {winner_name} for ₹{pick.winning_bid}L!"
            })

    except asyncio.CancelledError:
        # A new bid was placed before 15s ended. Cancel this thread cleanly!
        pass