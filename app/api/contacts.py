from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.db.repositories.user_repository import UserRepository
from app.dependencies.auth import get_current_user_id

router = APIRouter(prefix="/contacts", tags=["contacts"])

@router.get("")
def list_contacts(
    current_user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    users = UserRepository(db).list_users()
    return[
        {
            "userID": user.user_id,
            "displayName": user.display_name,
        }
        for user in users
        if user.user_id != current_user_id
    ]