import urllib.request
import urllib.parse
import xml.etree.ElementTree as ET
import hashlib
import ssl
from typing import List, Optional
from fastapi import APIRouter, Query
from app.schemas.core import NewsArticle

router = APIRouter()

def format_human_time(rfc_date_str: str) -> str:
    """Transforms raw RFC date strings into scannable timestamps."""
    try:
        parts = rfc_date_str.split()
        if len(parts) >= 5:
            # Returns format like: "25 Jun at 14:30"
            return f"{parts[1]} {parts[2]} at {parts[4][:5]}"
    except Exception:
        pass
    return "Recent"


def scrape_live_wire(query_string: str, category_label: str, max_items: int = 6) -> List[dict]:
    """
    Hits Google News XML syndication pipe.
    Enforces strict chronological sorting (&scoring=n) to prevent stale 'sticky' news.
    """
    encoded_query = urllib.parse.quote(query_string)
    
    # &scoring=n forces strictly newest-first sorting rather than algorithmic relevance
    url = f"https://news.google.com/rss/search?q={encoded_query}&hl=en-IN&gl=IN&ceid=IN:en&scoring=n"

    ssl_context = ssl.create_default_context()
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl.CERT_NONE

    req = urllib.request.Request(
        url, 
        headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}
    )

    scraped_list = []
    try:
        with urllib.request.urlopen(req, timeout=6, context=ssl_context) as response:
            xml_data = response.read()
            root = ET.fromstring(xml_data)

            for item in root.findall('./channel/item')[:max_items]:
                raw_title = item.find('title').text if item.find('title') is not None else ""
                
                if " - " in raw_title:
                    clean_title, _, source_fallback = raw_title.rpartition(" - ")
                else:
                    clean_title = raw_title
                    source_fallback = "Press Wire"

                source_node = item.find('source')
                source_name = source_node.text if source_node is not None else source_fallback

                raw_date = item.find('pubDate').text if item.find('pubDate') is not None else ""
                timestamp = format_human_time(raw_date)

                words = clean_title.split()
                derived_tags = [w.replace(":", "").replace(",", "").replace("'", "") for w in words if len(w) > 3 and w[0].isupper()][:3]
                if not derived_tags:
                    derived_tags = [category_label.title(), "Live Wire"]

                impact = "Medium Impact"
                upper_t = clean_title.upper()
                if any(w in upper_t for w in ["INJURY", "SQUAD", "RULED OUT", "BCCI", "ICC", "FINAL", "CHAMPIONS"]):
                    impact = "Critical"
                elif any(w in upper_t for w in ["TARGET", "STRIKE", "CENTURY", "DEBUT", "WIN", "REPORT"]):
                    impact = "High Impact"

                article_id = hashlib.md5(clean_title.encode('utf-8')).hexdigest()[:8]

                scraped_list.append({
                    "id": f"{category_label}-{article_id}",
                    "title": clean_title,
                    "summary": f"Live wire report captured via {source_name}. Telemetry syndicated directly from primary regional sports desk.",
                    "category": category_label,
                    "source_wire": source_name,
                    "published_time": timestamp,
                    "impact_level": impact,
                    "tags": derived_tags
                })

    except Exception as e:
        print(f"⚠️ Live Scraper Exception ({category_label}): {str(e)}")

    return scraped_list


@router.get("/feed", response_model=List[NewsArticle])
def get_live_intelligence_wire(category: Optional[str] = Query(None, description="Filter: 'domestic' or 'international'")):
    """Pulls live news on-demand with strict recency operators."""
    # Appending 'when:3d' / 'when:2d' acts as a hard filter against outdated press
    dom_query = '("Ranji Trophy" OR "Syed Mushtaq Ali" OR "Duleep Trophy" OR "TNPL" OR "Maharaja Trophy" OR "IPL scout" cricket) when:3d'
    int_query = '("ICC World Test Championship" OR "Border Gavaskar" OR "ODI cricket" OR "T20I cricket" OR "Test match") when:2d'

    if category == "domestic":
        return scrape_live_wire(dom_query, "domestic", 12)
    elif category == "international":
        return scrape_live_wire(int_query, "international", 12)
    
    return scrape_live_wire(dom_query, "domestic", 6) + scrape_live_wire(int_query, "international", 6)