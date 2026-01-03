import os
from dotenv import load_dotenv
import pymysql
import sys

# Load .env explicitly
env_path = os.path.join(os.path.dirname(__file__), '.env')
load_dotenv(env_path)

print("--- Testing Database Connection ---")
print(f"Loading .env from: {env_path}")

db_url = os.getenv("DATABASE_URL")
if not db_url:
    print("ERROR: DATABASE_URL not found in .env")
    sys.exit(1)

# Mask password for display
safe_url = db_url.split(":")[2].split("@")[1] if ":" in db_url and "@" in db_url else "HIDDEN"
print(f"URL found (masked): ...{safe_url}...")

try:
    # Parse URL manually to be sure
    # Format: mysql+pymysql://USER:PASS@HOST/DBNAME
    from sqlalchemy.engine.url import make_url
    url = make_url(db_url)
    
    print(f"Attempting to connect to:")
    print(f"  Host: {url.host}")
    print(f"  User: {url.username}")
    print(f"  DB:   {url.database}")
    print(f"  Port: {url.port}")
    
    connection = pymysql.connect(
        host=url.host,
        user=url.username,
        password=url.password,
        database=url.database,
        port=url.port or 3306,
        cursorclass=pymysql.cursors.DictCursor
    )
    
    print("\nSUCCESS! Connection established.")
    
    with connection.cursor() as cursor:
        cursor.execute("SELECT VERSION()")
        result = cursor.fetchone()
        print(f"Server Version: {result}")
        
    connection.close()
    
except Exception as e:
    print(f"\nFAILED: {str(e)}")
    print("\nPossible causes:")
    print("1. Wrong Password (check .env)")
    print("2. User not added to Database (check cPanel)")
    print("3. Host is not 127.0.0.1 or localhost")
