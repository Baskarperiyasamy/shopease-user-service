from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.security import AuthUser, get_auth_user
from app.database.connection import get_db
from app.models.user_model import UserProfile
from app.routers.dependencies import get_active_profile, get_current_profile
from app.schemas.user_schema import (
    AccountOut,
    ContactUpdate,
    MessageOut,
    ProfileCreate,
    ProfileOut,
    ProfilePatch,
    ProfileUpdate,
)
from app.services import user_service

router = APIRouter(prefix="/api/users", tags=["User Profile"])


@router.post("/profile", response_model=ProfileOut, status_code=status.HTTP_201_CREATED)
def create_profile(
    data: ProfileCreate,
    auth_user: AuthUser = Depends(get_auth_user),
    db: Session = Depends(get_db),
):
    return user_service.create_profile(db, auth_user.id, data)


@router.get("/profile", response_model=ProfileOut)
def get_profile(profile: UserProfile = Depends(get_current_profile)):
    return profile


@router.put("/profile", response_model=ProfileOut)
def update_profile(
    data: ProfileUpdate,
    profile: UserProfile = Depends(get_active_profile),
    db: Session = Depends(get_db),
):
    return user_service.replace_profile(db, profile, data)


@router.patch("/profile", response_model=ProfileOut)
def patch_profile(
    data: ProfilePatch,
    profile: UserProfile = Depends(get_active_profile),
    db: Session = Depends(get_db),
):
    return user_service.patch_profile(db, profile, data)


@router.delete("/profile", response_model=MessageOut)
def delete_profile(
    profile: UserProfile = Depends(get_current_profile),
    db: Session = Depends(get_db),
):
    user_service.delete_profile(db, profile)
    return MessageOut(message="Profile and saved addresses deleted successfully")


@router.patch("/profile/contact", response_model=ProfileOut)
def update_contact(
    data: ContactUpdate,
    profile: UserProfile = Depends(get_active_profile),
    db: Session = Depends(get_db),
):
    return user_service.update_contact(db, profile, data)


@router.post("/profile/deactivate", response_model=ProfileOut)
def deactivate_profile(
    profile: UserProfile = Depends(get_current_profile),
    db: Session = Depends(get_db),
):
    return user_service.set_profile_active(db, profile, False)


@router.post("/profile/reactivate", response_model=ProfileOut)
def reactivate_profile(
    profile: UserProfile = Depends(get_current_profile),
    db: Session = Depends(get_db),
):
    return user_service.set_profile_active(db, profile, True)


@router.get("/account", response_model=AccountOut)
def get_account(
    auth_user: AuthUser = Depends(get_auth_user),
    profile: UserProfile = Depends(get_current_profile),
):
    default_address = next((a for a in profile.addresses if a.is_default), None)
    return AccountOut(
        auth_user_id=auth_user.id,
        role=auth_user.role,
        profile=profile,
        address_count=len(profile.addresses),
        default_address=default_address,
    )
