from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.security import AuthUser, get_auth_user
from app.database.connection import get_db
from app.models.user_model import UserProfile
from app.services import user_service


def get_current_profile(
    auth_user: AuthUser = Depends(get_auth_user),
    db: Session = Depends(get_db),
) -> UserProfile:
    profile = user_service.get_profile_by_auth_id(db, auth_user.id)
    if profile is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Profile not found. Create your profile first",
        )
    return profile


def get_active_profile(profile: UserProfile = Depends(get_current_profile)) -> UserProfile:
    if not profile.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Profile is deactivated. Reactivate it to continue",
        )
    return profile
