from database import SessionLocal, User, init_db
from auth import verify_password, get_password_hash
import os

# Ensure tables exist (important for new DB)
init_db()

db = SessionLocal()
username = os.getenv("ADMIN_USERNAME", "phongdh")
secure_pass = os.getenv("ADMIN_PASSWORD")

if not secure_pass:
    raise RuntimeError("ADMIN_PASSWORD environment variable is required.")

print(f"--- SETTING SECURE PASSWORD FOR: {username} ---")

user = db.query(User).filter(User.username == username).first()
if user:
    user.hashed_password = get_password_hash(secure_pass)
    print("✅ Password updated to secure version.")
else:
    print("User not found. Creating user...")
    user = User(username=username, hashed_password=get_password_hash(secure_pass))
    db.add(user)
    print("✅ User created with secure password.")

db.commit()

# Verify
if verify_password(secure_pass, user.hashed_password):
    print("✅ Verification OK")
else:
    print("❌ Verification FAILED")

db.close()
