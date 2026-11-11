from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, field_validator, model_validator

from app.schemas.address_schema import AddressOut
from app.schemas.validators import PersonName, clean_phone

Gender = Literal["male", "female", "other", "prefer_not_to_say"]


def check_birth_date(value: date | None) -> date | None:
    if value is None:
        return None
    if value > date.today():
        raise ValueError("Date of birth cannot be in the future")
    if value.year < 1900:
        raise ValueError("Date of birth is not valid")
    return value


def normalize_gender(value):
    if isinstance(value, str):
        return value.strip().lower().replace(" ", "_")
    return value


def check_image(value: str | None) -> str | None:
    if value is None:
        return None
    value = value.strip()
    if len(value) > 255:
        raise ValueError("profile_image must not be longer than 255 characters")
    return value or None


class ProfileCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    full_name: PersonName
    phone_number: str
    date_of_birth: date | None = None
    gender: Gender | None = None
    profile_image: str | None = None

    @field_validator("phone_number")
    @classmethod
    def check_phone(cls, value: str) -> str:
        return clean_phone(value)

    @field_validator("date_of_birth")
    @classmethod
    def check_dob(cls, value: date | None) -> date | None:
        return check_birth_date(value)

    @field_validator("gender", mode="before")
    @classmethod
    def check_gender(cls, value):
        return normalize_gender(value)

    @field_validator("profile_image")
    @classmethod
    def check_profile_image(cls, value: str | None) -> str | None:
        return check_image(value)


class ProfileUpdate(ProfileCreate):
    pass


class ProfilePatch(BaseModel):
    model_config = ConfigDict(extra="forbid")

    full_name: PersonName | None = None
    phone_number: str | None = None
    date_of_birth: date | None = None
    gender: Gender | None = None
    profile_image: str | None = None

    @field_validator("phone_number")
    @classmethod
    def check_phone(cls, value: str | None) -> str | None:
        return clean_phone(value) if value is not None else None

    @field_validator("date_of_birth")
    @classmethod
    def check_dob(cls, value: date | None) -> date | None:
        return check_birth_date(value)

    @field_validator("gender", mode="before")
    @classmethod
    def check_gender(cls, value):
        return normalize_gender(value)

    @field_validator("profile_image")
    @classmethod
    def check_profile_image(cls, value: str | None) -> str | None:
        return check_image(value)

    @model_validator(mode="after")
    def required_fields_not_null(self):
        for name in ("full_name", "phone_number"):
            if name in self.model_fields_set and getattr(self, name) is None:
                raise ValueError(f"{name} cannot be set to null")
        return self


class ContactUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    phone_number: str

    @field_validator("phone_number")
    @classmethod
    def check_phone(cls, value: str) -> str:
        return clean_phone(value)


class ProfileOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    auth_user_id: int
    full_name: str
    phone_number: str
    date_of_birth: date | None
    gender: str | None
    profile_image: str | None
    is_active: bool
    created_at: datetime
    updated_at: datetime


class AccountOut(BaseModel):
    auth_user_id: int
    role: str
    profile: ProfileOut
    address_count: int
    default_address: AddressOut | None


class MessageOut(BaseModel):
    message: str
