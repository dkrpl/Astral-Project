import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.database import SessionLocal
from app.models.user import User
from app.utils.security import get_password_hash

def create_superadmin():
    db = SessionLocal()
    try:
        # Check if superadmin already exists
        existing = db.query(User).filter(User.is_superadmin == True).first()
        if existing:
            print(f"Superadmin already exists: {existing.username}")
            return
        
        # Create superadmin
        superadmin = User(
            email="admin@astral.com",
            username="superadmin",
            full_name="System Super Administrator",
            hashed_password=get_password_hash("admin123"),
            is_active=True,
            is_admin=True,
            is_superadmin=True
        )
        
        db.add(superadmin)
        db.commit()
        db.refresh(superadmin)
        
        print("Superadmin created successfully!")
        print(f"Username: superadmin")
        print(f"Password: admin123")
        print("Please change the password immediately after first login!")
        
    except Exception as e:
        print(f"Error creating superadmin: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    create_superadmin()