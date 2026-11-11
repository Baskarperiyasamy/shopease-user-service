from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database.connection import safe_commit
from app.models.user_model import UserProfile
from app.schemas.user_schema import ContactUpdate, ProfileCreate, ProfilePatch, ProfileUpdate


def get_profile_by_auth_id(db: Session, auth_user_id: int) -> UserProfile | None:
    return db.scalar(select(UserProfile).where(UserProfile.auth_user_id == auth_user_id))


def create_profile(db: Session, auth_user_id: int, data: ProfileCreate) -> UserProfile:
    if get_profile_by_auth_id(db, auth_user_id):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Profile already exists for this user")

    profile = UserProfile(auth_user_id=auth_user_id, **data.model_dump())
    db.add(profile)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Profile already exists for this user")
    db.refresh(profile)
    return profile


def replace_profile(db: Session, profile: UserProfile, data: ProfileUpdate) -> UserProfile:
    for field, value in data.model_dump().items():
        setattr(profile, field, value)
    safe_commit(db)
    db.refresh(profile)
    return profile


def patch_profile(db: Session, profile: UserProfile, data: ProfilePatch) -> UserProfile:
    changes = data.model_dump(exclude_unset=True)
    if not changes:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No fields provided to update")
    for field, value in changes.items():
        setattr(profile, field, value)
    safe_commit(db)
    db.refresh(profile)
    return profile


def update_contact(db: Session, profile: UserProfile, data: ContactUpdate) -> UserProfile:
    profile.phone_number = data.phone_number
    safe_commit(db)
    db.refresh(profile)
    return profile


def set_profile_active(db: Session, profile: UserProfile, active: bool) -> UserProfile:
    if profile.is_active == active:
        state = "active" if active else "deactivated"
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Profile is already {state}")
    profile.is_active = active
    safe_commit(db)
    db.refresh(profile)
    return profile


def delete_profile(db: Session, profile: UserProfile) -> None:
    db.delete(profile)
    safe_commit(db)
