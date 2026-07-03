import os
import time
import requests
import json
from sqlalchemy.orm import Session
from groq import Groq

from app.core.database import SessionLocal
from app.models.core import Player
from app.core.config import settings

# Initialize Groq
client = Groq(api_key=settings.GROQ_API_KEY)

# Medical Triage Lexicon
MEDICAL_KEYWORDS = [
    "injur", "surger", "fractur", "hamstring", "ruled out", "rehab", 
    "ligament", "concussion", "knee", "ankle", "back", "groin", 
    "shoulder", "withdrew", "missed", "fitness", "tear", "strain"
]

def fetch_full_wikipedia_text(player_name: str) -> str:
    """Hits the MediaWiki API to pull the raw, unformatted plaintext of the entire page."""
    session = requests.Session()
    url = "https://en.wikipedia.org/w/api.php"
    
    params = {
        "action": "query",
        "format": "json",
        "prop": "extracts",
        "explaintext": True, # Forces plain text instead of HTML
        "redirects": 1,
        "titles": player_name
    }
    
    headers = {"User-Agent": "CrickAI_Medical_Scraper/1.0 (Contact: localdev@crickai.org)"}
    
    try:
        response = session.get(url=url, params=params, headers=headers, timeout=10)
        data = response.json()
        pages = data["query"]["pages"]
        page_id = list(pages.keys())[0]
        
        if page_id == "-1":
            return ""
            
        return pages[page_id].get("extract", "")
    except Exception:
        return ""

def triage_medical_paragraphs(full_text: str) -> str:
    """Pre-filter: Scans the text and returns ONLY paragraphs containing medical keywords."""
    if not full_text:
        return ""
        
    paragraphs = full_text.split("\n")
    danger_chunks = []
    
    for p in paragraphs:
        # If any medical word appears in this paragraph, save it
        if any(keyword in p.lower() for keyword in MEDICAL_KEYWORDS):
            danger_chunks.append(p.strip())
            
    if not danger_chunks:
        return "NO_MEDICAL_MENTIONS"
        
    # Join them and cap at 3,500 characters just as a secondary safety net
    return "\n".join(danger_chunks)[:3500]

def generate_medical_summary(dossier_text: str, player_name: str) -> str:
    """Asks Groq to turn the raw triage paragraphs into a clean 2-sentence report."""
    if dossier_text == "NO_MEDICAL_MENTIONS" or not dossier_text:
        return "No major historical injuries or chronic fitness issues documented on public record."

    system_prompt = f"""
    You are an elite sports medical archivist. 
    Analyze the provided text snippets scraped from cricketer {player_name}'s Wikipedia record.
    
    Your task: Output a crisp, highly professional, 2-sentence 'Injury & Durability Profile'.
    
    RULES:
    1. Focus strictly on chronic issues, surgeries, major fractures, or missed tournaments.
    2. Do NOT use conversational filler (e.g. do not start with "Based on the text...").
    3. If the snippets talk about an injury but it was minor/resolved instantly with no missing time, treat it as clean.
    """

    try:
        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"RAW DOSSIER FOR {player_name}:\n{dossier_text}"}
            ],
            temperature=0.2
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"   [!] Groq API Error for {player_name}: {str(e)}")
        return "Medical history temporarily unavailable due to API timeout."

def run_injury_backfill():
    db: Session = SessionLocal()
    
    # Grab players who don't have an injury profile generated yet
    players = db.query(Player).filter(Player.injury_profile == None).all()
    
    print(f"\n🏥 STARTING MEDICAL DOSSIER BACKFILL ({len(players)} players remaining)")
    print("="*60)
    
    for idx, player in enumerate(players, 1):
        print(f"[{idx}/{len(players)}] Scanning Wikipedia for: {player.name}...")
        
        # 1. Fetch raw text
        raw_wiki = fetch_full_wikipedia_text(player.name)
        
        # 2. Triage the text locally (Saves 90% of tokens)
        triaged_dossier = triage_medical_paragraphs(raw_wiki)
        
        # 3. Send condensed dossier to Groq
        summary = generate_medical_summary(triaged_dossier, player.name)
        
        # 4. Save to DB
        player.injury_profile = summary
        db.commit()
        
        print(f"   ↳ {summary[:75]}...\n")
        
        # Gentle 1.5-second governor to guarantee we never trigger Groq's TPM alarm
        time.sleep(1.5)

    print("="*60)
    print("✅ MEDICAL BACKFILL COMPLETE.")
    db.close()

if __name__ == "__main__":
    run_injury_backfill()