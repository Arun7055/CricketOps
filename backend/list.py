import csv
import os
from sqlalchemy.orm import Session
from app.core.database import SessionLocal
from app.models.core import Player

def sync_player_roster(file_path: str):
    """
    Master Database Seeder: Reads the source CSV to perform an 'Upsert' (Update or Insert).
    - New Players: Instantly created with Name, Role, Batting, and Bowling styles.
    - Existing Players: Checked against the CSV; updates are committed ONLY if the data differs.
    """
    db: Session = SessionLocal()
    
    # 1. Load existing DB into an O(1) lookup dictionary: { "Virat Kohli": <Player Object> }
    # This prevents us from spamming Neon DB with 500 individual SELECT queries inside the loop.
    existing_players = {p.name: p for p in db.query(Player).all()}
    
    new_players_to_add = []
    stats = {"inserted": 0, "updated": 0, "unchanged": 0}
    
    try:
        with open(file_path, mode='r', encoding='utf-8-sig') as file:
            reader = csv.DictReader(file)
            
            for row in reader:
                name = row.get('name', '').strip()
                if not name:
                    continue
                    
                role = row.get('role', '').strip() or "Unknown"
                batting = row.get('batting_style', '').strip() or "Unknown"
                bowling = row.get('bowling_style', '').strip() or "Does not bowl"

                # SCENARIO A: Player exists -> Perform a "Dirty Check" for changed data
                if name in existing_players:
                    player = existing_players[name]
                    needs_update = False
                    
                    if player.role != role and role != "Unknown":
                        player.role = role
                        needs_update = True
                    if player.batting_style != batting and batting != "Unknown":
                        player.batting_style = batting
                        needs_update = True
                    if player.bowling_style != bowling and bowling != "Does not bowl":
                        player.bowling_style = bowling
                        needs_update = True

                    if needs_update:
                        stats["updated"] += 1
                    else:
                        stats["unchanged"] += 1

                # SCENARIO B: Brand new player -> Stage for bulk insert
                else:
                    new_player = Player(
                        name=name,
                        role=role,
                        batting_style=batting,
                        bowling_style=bowling
                    )
                    new_players_to_add.append(new_player)
                    
                    # Immediately cache them in our lookup dictionary so duplicate rows in the CSV don't break us
                    existing_players[name] = new_player 
                    stats["inserted"] += 1

        # 2. Execute a single Atomic PostgreSQL Transaction
        if new_players_to_add:
            db.bulk_save_objects(new_players_to_add)
            
        db.commit()
        
        # 3. Print a clean, scannable CLI readout for the developer
        print("\n" + "="*45)
        print(" 🏏 NEON DB ROSTER SYNCHRONIZATION COMPLETE")
        print("="*45)
        print(f" New Players Added : +{stats['inserted']}")
        print(f" Profiles Updated  : ~{stats['updated']}")
        print(f" Pristine/Skipped  :  {stats['unchanged']}")
        print(f" Total Roster Size :  {len(existing_players)}")
        print("="*45 + "\n")

    except FileNotFoundError:
        print(f"\n❌ CRITICAL: Master CSV not found at path -> {file_path}")
    except Exception as e:
        print(f"\n❌ DATABASE TRANSACTION ABORTED: {str(e)}")
        db.rollback() # Safe rollback prevents partial data corruption
    finally:
        db.close()

if __name__ == "__main__":
    current_dir = os.path.dirname(os.path.abspath(__file__))
    target_csv = os.path.join(current_dir, "listt.csv")
    
    sync_player_roster(target_csv)