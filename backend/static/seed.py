import csv
from sqlalchemy.orm import Session
from app.core.database import SessionLocal
from app.models.core import Player

def update_base_prices(file_path: str):
    db: Session = SessionLocal()
    updated_count = 0
    
    try:
        # utf-8-sig removes any hidden BOM characters from Excel exports
        with open(file_path, mode='r', encoding='utf-8-sig') as file:
            reader = csv.DictReader(file)
            
            for row in reader:
                # Adjust these keys if your CSV headers are named differently (e.g., 'Player Name')
                player_name = row.get("name") or row.get("Player Name")
                base_price_raw = row.get("Base Price")

                if player_name and base_price_raw:
                    # Find the player in Neon DB
                    player = db.query(Player).filter(Player.name == player_name.strip()).first()
                    
                    if player:
                        # Clean the price string (turns "50L" or "₹ 50" into pure integer 50)
                        clean_price = ''.join(filter(str.isdigit, str(base_price_raw)))
                        if clean_price:
                            player.base_price = int(clean_price)
                            updated_count += 1
        
        db.commit()
        print(f"✅ Success! Updated {updated_count} players with base prices.")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    # Ensure this points to where your list.csv is located!
    update_base_prices("listt.csv")