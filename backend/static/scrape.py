import requests
from app.core.database import SessionLocal
from app.models.core import Player

def format_wikipedia_title(name: str) -> str:
    """
    Converts a player name into a standard Wikipedia URL title.
    """
    # Standardize capitalization and replace spaces with underscores
    clean_name = name.strip().title().replace(" ", "_")
    
    # The Master Translation Dictionary for tricky spellings or Wikipedia disambiguations
    disambiguations = {
        "Ms_Dhoni": "MS_Dhoni",
        "Kl_Rahul": "KL_Rahul",
        "Md_Shami": "Mohammed_Shami",
        "Mujeeb_Rahman": "Mujeeb_Ur_Rahman",
        "Am_Ghazanfar": "Allah_Mohammad_Ghazanfar",
        "Jake_Fraser-Mcgurk": "Jake_Fraser-McGurk",
        "Mayank_Agarawal": "Mayank_Agarwal",
        "Kunal_Rathore": "Kunal_Rathore_(cricketer)",
        "Rashid_Khan": "Rashid_Khan_(Afghan_cricketer)" 
    }
    
    return disambiguations.get(clean_name, clean_name)

def scrape_wikipedia_deep_profiles():
    db = SessionLocal()
    players = db.query(Player).all()
    
    headers = {
        'User-Agent': 'CricketAnalyticsAI/3.0 (your-email@example.com) Python-Requests'
    }

    print(f"Starting Deep Wikipedia Extraction for {len(players)} players...")

    for player in players:
        wiki_title = format_wikipedia_title(player.name)
        
        # Using the Action API to get the full introductory text without HTML
        url = "https://en.wikipedia.org/w/api.php"
        params = {
            "action": "query",
            "format": "json",
            "titles": wiki_title,
            "prop": "extracts",
            "exintro": True,
            "explaintext": True,
            "redirects": 1
        }
        
        try:
            response = requests.get(url, headers=headers, params=params, timeout=5)
            
            if response.status_code == 200:
                data = response.json()
                pages = data.get("query", {}).get("pages", {})
                
                page_data = next(iter(pages.values()))
                
                if "missing" in page_data:
                    print(f"❌ Page not found on Wikipedia for title: {wiki_title}")
                else:
                    biography = page_data.get("extract", "").strip()
                    
                    if biography and len(biography) > 50:
                        # Overwrites existing short profiles with the new dense text
                        player.cricbuzz_profile = biography
                        db.commit()
                        print(f"✅ Extracted rich biography for: {player.name} ({len(biography)} chars)")
                    else:
                        print(f"⚠️ Extract too short or missing for: {player.name}")
                        
            else:
                print(f"⚠️ Failed to fetch {player.name} (Status Code: {response.status_code})")
                
        except Exception as e:
            print(f"Error processing {player.name}: {str(e)}")

    db.close()
    print("\nDeep database sync pipeline complete!")

if __name__ == "__main__":
    scrape_wikipedia_deep_profiles()