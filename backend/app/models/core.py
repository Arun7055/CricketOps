import uuid
from sqlalchemy import Column, String, Integer, Float, Boolean, Date, ForeignKey, Text, UUID
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.core.database import Base

class Player(Base):
    __tablename__ = "players"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    role = Column(String(50), nullable=False)
    batting_style = Column(String(50))
    bowling_style = Column(String(50))
    birth_date = Column(Date, nullable=True)
    current_team = Column(String(100))
    cricbuzz_profile = Column(Text, nullable=True)
    injury_profile = Column(Text, nullable=True)
    base_price = Column(Integer, default=50) # Storing in Lakhs (50 = 50 Lakhs)


class MatchupPvP(Base):
    __tablename__ = "matchups_pvp"

    id = Column(Integer, primary_key=True, index=True)
    
    # CHANGED: These are now UUIDs instead of Integers
    batter_id = Column(UUID(as_uuid=True), ForeignKey("players.id", ondelete="CASCADE"), nullable=False, index=True)
    bowler_id = Column(UUID(as_uuid=True), ForeignKey("players.id", ondelete="CASCADE"), nullable=False, index=True)

    runs_scored = Column(Integer, default=0)
    balls_faced = Column(Integer, default=0)
    dismissals = Column(Integer, default=0)
    dots_faced = Column(Integer, default=0)

    batter = relationship("Player", foreign_keys=[batter_id])
    bowler = relationship("Player", foreign_keys=[bowler_id])


class VenueMastery(Base):
    __tablename__ = "venue_mastery"

    id = Column(Integer, primary_key=True, index=True)
    
    # CHANGED: This is now a UUID instead of an Integer
    player_id = Column(UUID(as_uuid=True), ForeignKey("players.id", ondelete="CASCADE"), nullable=False, index=True)
    venue_normalized = Column(String, nullable=False, index=True) 

    bat_runs = Column(Integer, default=0)
    bat_balls = Column(Integer, default=0)
    bat_dismissals = Column(Integer, default=0)

    bowl_balls = Column(Integer, default=0)
    bowl_runs_conceded = Column(Integer, default=0)
    bowl_wickets = Column(Integer, default=0)

    player = relationship("Player", foreign_keys=[player_id])

class Lobby(Base):
    __tablename__ = "auction_lobbies"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    room_code = Column(String, unique=True, index=True, nullable=False) # e.g., "XYZ-123"
    status = Column(String, default="waiting") # waiting, live, simulation, completed
    
    # Tactical settings chosen by the lobby host
    venue_selected = Column(String, nullable=True) 
    format_selected = Column(String, nullable=True)

    # Active Auction State (Updated constantly via RabbitMQ worker)
    current_player_id = Column(UUID(as_uuid=True), ForeignKey("players.id", ondelete="SET NULL"), nullable=True)
    current_bid = Column(Integer, default=0)
    highest_bidder_id = Column(UUID(as_uuid=True), ForeignKey("participants.id", ondelete="SET NULL"), nullable=True)

class Participant(Base):
    __tablename__ = "participants"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    lobby_id = Column(UUID(as_uuid=True), ForeignKey("auction_lobbies.id", ondelete="CASCADE"), nullable=False, index=True)
    username = Column(String, nullable=False)
    
    purse_remaining = Column(Integer, default=10000) # 100.00 Crores represented as 10,000 Lakhs
    squad_size = Column(Integer, default=0)

class DraftPick(Base):
    __tablename__ = "draft_picks"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    lobby_id = Column(UUID(as_uuid=True), ForeignKey("auction_lobbies.id", ondelete="CASCADE"), nullable=False, index=True)
    participant_id = Column(UUID(as_uuid=True), ForeignKey("participants.id", ondelete="CASCADE"), nullable=True, index=True)
    player_id = Column(UUID(as_uuid=True), ForeignKey("players.id", ondelete="CASCADE"), nullable=False)
    
    sold_price = Column(Integer, nullable=False)