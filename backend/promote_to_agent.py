"""
One-time script: promote a user to the 'agent' role for testing.
Run with: python promote_to_agent.py
Delete this file once you're done testing.
"""

from app.database import SessionLocal
from app.models.user import User, RoleEnum

EMAIL_TO_PROMOTE = "kavya0308181@gmail.com"

db = SessionLocal()
try:
    user = db.query(User).filter(User.email == EMAIL_TO_PROMOTE).first()
    if not user:
        print(f"No user found with email: {EMAIL_TO_PROMOTE}")
    else:
        user.role = RoleEnum.admin
        db.commit()
        print(f"Success: {user.email} is now role = {user.role.value}")
finally:
    db.close()
