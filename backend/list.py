import csv
import os
from app.core.database import SessionLocal
from app.models.core import Player

def update_styles_from_csv(file_path: str):
    db = SessionLocal()
    
    updated_count = 0
    not_found_count = 0
    
    try:
        with open(file_path, mode='r', encoding='utf-8-sig') as file:
            reader = csv.DictReader(file)
            
            for row in reader:
                name = row.get('name', '').strip()
                
                # Make sure these match your exact CSV column headers!
                batting = row.get('batting_style', '').strip() 
                bowling = row.get('bowling_style', '').strip() 
                
                if not name:
                    continue
                    
                # 1. Look up the existing player in the database
                player = db.query(Player).filter(Player.name == name).first()
                
                if player:
                    # 2. Update ONLY the batting and bowling columns
                    player.batting_style = batting if batting else "Unknown"
                    player.bowling_style = bowling if bowling else "Does not bowl"
                    updated_count += 1
                else:
                    # If someone is in the CSV but got deleted from the DB, just skip them
                    print(f"⚠️ Player '{name}' found in CSV but not in Database. Skipping.")
                    not_found_count += 1

        # 3. Save all the targeted updates to Neon
        db.commit()
        print(f"✅ Successfully updated batting & bowling styles for {updated_count} players.")
        
        if not_found_count > 0:
            print(f"⚠️ Skipped {not_found_count} rows that didn't match existing DB players.")
            
    except FileNotFoundError:
        print(f"❌ Could not find the file: {file_path}")
    except Exception as e:
        print(f"❌ An error occurred: {str(e)}")
        db.rollback() # Safely roll back if there is a database crash
    finally:
        db.close()

if __name__ == "__main__":
    # OS Path resolution so it finds listt.csv safely
    current_dir = os.path.dirname(os.path.abspath(__file__))
    csv_path = os.path.join(current_dir, "listt.csv")
    
    print("Scanning database for matching players to update...")
    update_styles_from_csv(csv_path)