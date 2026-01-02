import pymysql
import os
from dotenv import load_dotenv

load_dotenv()

database_url = os.getenv("DATABASE_URL")
# Parse URL roughly: mysql+pymysql://user:pass@host/dbname
# This is a quick hack, better to use sqlalchemy.engine.url but this avoids imports
try:
    # Remove prefix
    url_noprefix = database_url.replace("mysql+pymysql://", "")
    
    # Split User:Pass and Host/DB
    if "@" in url_noprefix:
        auth_part, rest = url_noprefix.split("@")
        host_db = rest
    else:
        # No auth? Unlikely for mysql
        auth_part = ":"
        host_db = url_noprefix

    if ":" in auth_part:
        user = auth_part.split(":")[0]
        password = auth_part.split(":")[1]
    else:
        user = auth_part
        password = ""

    if "/" in host_db:
        host, db_name = host_db.split("/")
    else:
        host = host_db
        db_name = "imapsync_db" # Default

except Exception as e:
    print(f"Error parsing DATABASE_URL: {e}")
    # Fallback to defaults if parsing fails or for testing
    exit(1)

print(f"Connecting to {host} as {user}...")

try:
    connection = pymysql.connect(
        host=host,
        user=user,
        password=password,
        cursorclass=pymysql.cursors.DictCursor
    )

    with connection.cursor() as cursor:
        print(f"Creating database {db_name} if not exists...")
        cursor.execute(f"CREATE DATABASE IF NOT EXISTS {db_name}")
        print("Database created or already exists.")
    
    connection.close()
except Exception as e:
    print(f"Error connecting to MariaDB: {e}")
