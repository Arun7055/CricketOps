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

    stats = relationship("PlayerMatchStat", back_populates="player", cascade="all, delete-orphan")

class PlayerMatchStat(Base):
    __tablename__ = "player_match_stats"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    player_id = Column(UUID(as_uuid=True), ForeignKey("players.id", ondelete="CASCADE"))
    match_date = Column(Date, nullable=False)
    format = Column(String(10), nullable=False)
    venue = Column(String(255), nullable=False)
    opposition = Column(String(100), nullable=False)
    runs_scored = Column(Integer, default=0)
    balls_faced = Column(Integer, default=0)
    wickets_taken = Column(Integer, default=0)
    overs_bowled = Column(Float, default=0.0)
    runs_conceded = Column(Integer, default=0)
    injury_sustained = Column(Boolean, default=False)
    
    player = relationship("Player", back_populates="stats")

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