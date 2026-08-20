import sqlite3
import time
import requests
import feedparser
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut

# --- 1. DATABASE CONFIGURATION ---
DB_NAME = "ocean_alerts.db"

def setup_database():
    """Initializes SQLite database and creates the alerts table."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS alerts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source_platform TEXT,
            title TEXT UNIQUE,
            published_at TEXT,
            source_url TEXT,
            location_name TEXT,
            latitude REAL,
            longitude REAL,
            severity TEXT
        )
    ''')
    conn.commit()
    conn.close()
    print(" Database initialized.")

# --- 2. LOCATION EXTRACTION ---
INDIAN_COASTAL_CITIES = [
    "Chennai", "Mumbai", "Kochi", "Kolkata", "Visakhapatnam", 
    "Vizag", "Puri", "Goa", "Mangalore", "Andaman", "Odisha", 
    "Bengal", "Gujarat", "Kerala", "Tamil Nadu"
]

def extract_location(text):
    """Matches text against known coastal regions."""
    for city in INDIAN_COASTAL_CITIES:
        if city.lower() in text.lower():
            # Standardize Vizag -> Visakhapatnam for geocoding accuracy
            mapped_city = "Visakhapatnam" if city.lower() == "vizag" else city
            return f"{mapped_city}, India"
    return None

# --- 3. GEOCODING ---
geolocator = Nominatim(user_agent="ocean_monitor_hybrid_crawler")

def get_coordinates(location_name):
    """Converts extracted place name into Latitude and Longitude."""
    try:
        time.sleep(1)  # Respect OpenStreetMap rate limits (1 req/sec)
        location = geolocator.geocode(location_name)
        if location:
            return location.latitude, location.longitude
    except GeocoderTimedOut:
        print(f" Geocoder timed out for {location_name}")
    return None, None

def save_alert(cursor, platform, title, published, url, location, lat, lon):
    """Inserts a structured alert into SQLite."""
    severity = "Critical" if any(w in title.lower() for w in ["cyclone", "tsunami", "evacuate"]) else "Warning"
    cursor.execute('''
        INSERT INTO alerts (source_platform, title, published_at, source_url, location_name, latitude, longitude, severity)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', (platform, title, published, url, location, lat, lon, severity))
    print(f"[{platform}]  Mapped: {location} | {severity} | {title[:45]}...")

# --- 4. SOURCE 1: GOOGLE NEWS ---
def fetch_google_news(cursor):
    print("\n Sourcing: Google News RSS...")
    rss_url = "https://news.google.com/rss/search?q=cyclone+OR+tsunami+OR+flood+bay+of+bengal+india&hl=en-IN&gl=IN&ceid=IN:en"
    feed = feedparser.parse(rss_url)
    
    count = 0
    for entry in feed.entries[:10]:
        cursor.execute("SELECT id FROM alerts WHERE title = ?", (entry.title,))
        if cursor.fetchone():
            continue
        
        location = extract_location(entry.title)
        if location:
            lat, lon = get_coordinates(location)
            if lat and lon:
                save_alert(cursor, "Google News", entry.title, entry.published, entry.link, location, lat, lon)
                count += 1
    return count

# --- 5. SOURCE 2: REDDIT ---
def fetch_reddit_alerts(cursor):
    print("\n Sourcing: Reddit Subreddits...")
    
    # Targeting key regional subreddits for disaster/marine alerts
    subreddits = "india+chennai+mumbai+kerala+kolkata+odisha"
    query = "cyclone OR tsunami OR flood OR high tide OR storm"
    reddit_url = f"https://www.reddit.com/r/ {subreddits}/search.json?q={query}&sort=new&restrict_sr=1&limit=15".replace(" ", "")
    
    # Reddit blocks default Python requests; a custom User-Agent is mandatory
    headers = {"User-Agent": "ocean-monitor-bot:v1.0 (prototype)"}
    
    count = 0
    try:
        response = requests.get(reddit_url, headers=headers, timeout=10)
        if response.status_code == 200:
            posts = response.json().get("data", {}).get("children", [])
            for post in posts:
                data = post.get("data", {})
                title = data.get("title", "")
                selftext = data.get("selftext", "")
                url = f"https://reddit.com{data.get('permalink')}"
                created_utc = time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime(data.get("created_utc", 0)))
                
                # Check for duplicates
                cursor.execute("SELECT id FROM alerts WHERE title = ?", (title,))
                if cursor.fetchone():
                    continue

                # Search both title and post body for locations
                location = extract_location(title) or extract_location(selftext)
                if location:
                    lat, lon = get_coordinates(location)
                    if lat and lon:
                        save_alert(cursor, "Reddit", title, created_utc, url, location, lat, lon)
                        count += 1
        else:
            print(f" Reddit API returned status {response.status_code}")
    except Exception as e:
        print(f" Reddit fetch error: {e}")
        
    return count

# --- 6. EXECUTION ---
if __name__ == "__main__":
    setup_database()
    
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor() 
    
    news_count = fetch_google_news(cur)
    reddit_count = fetch_reddit_alerts(cur)
    
    conn.commit()
    conn.close()
    
    print(f"\n Pipeline Finished: {news_count} news alerts and {reddit_count} Reddit posts stored.")