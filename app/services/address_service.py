from fastapi import HTTPException, status
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.database.connection import safe_commit
from app.models.address_model import UserAddress
from app.models.user_model import UserProfile
from app.schemas.address_schema import AddressCreate, AddressUpdate


def lock_profile(db: Session, profile: UserProfile) -> None:
    db.execute(select(UserProfile.id).where(UserProfile.id == profile.id).with_for_update())


def clear_defaults(db: Session, profile_id: int, keep_id: int | None = None) -> None:
    statement = update(UserAddress).where(UserAddress.user_id == profile_id, UserAddress.is_default.is_(True))
    if keep_id is not None:
        statement = statement.where(UserAddress.id != keep_id)
    db.execute(statement.values(is_default=False))


def list_addresses(db: Session, profile: UserProfile) -> list[UserAddress]:
    return list(db.scalars(select(UserAddress).where(UserAddress.user_id == profile.id).order_by(UserAddress.id)))


def get_owned_address(db: Session, profile: UserProfile, address_id: int) -> UserAddress:
    address = db.get(UserAddress, address_id)
    if address is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Address not found")
    if address.user_id != profile.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not allowed to access this address",
        )
    return address


def create_address(db: Session, profile: UserProfile, data: AddressCreate) -> UserAddress:
    lock_profile(db, profile)
    existing_count = len(list_addresses(db, profile))
    values = data.model_dump()
    make_default = values["is_default"] or existing_count == 0
    values["is_default"] = make_default

    if make_default:
        clear_defaults(db, profile.id)
    address = UserAddress(user_id=profile.id, **values)
    db.add(address)
    safe_commit(db)
    db.refresh(address)
    return address


def update_address(db: Session, profile: UserProfile, address_id: int, data: AddressUpdate) -> UserAddress:
    address = get_owned_address(db, profile, address_id)
    lock_profile(db, profile)
    values = data.model_dump()
    wants_default = values.pop("is_default")

    for field, value in values.items():
        setattr(address, field, value)
    if wants_default:
        clear_defaults(db, profile.id, keep_id=address.id)
        address.is_default = True

    safe_commit(db)
    db.refresh(address)
    return address


def set_default_address(db: Session, profile: UserProfile, address_id: int) -> UserAddress:
    address = get_owned_address(db, profile, address_id)
    lock_profile(db, profile)
    clear_defaults(db, profile.id, keep_id=address.id)
    address.is_default = True
    safe_commit(db)
    db.refresh(address)
    return address


def delete_address(db: Session, profile: UserProfile, address_id: int) -> None:
    address = get_owned_address(db, profile, address_id)
    lock_profile(db, profile)
    was_default = address.is_default
    db.delete(address)
    db.flush()

    if was_default:
        remaining = list_addresses(db, profile)
        if remaining:
            remaining[0].is_default = True
    safe_commit(db)
