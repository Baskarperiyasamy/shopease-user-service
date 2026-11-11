from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, field_validator

from app.schemas.validators import LongText, PersonName, ShortText, clean_phone, clean_postal_code

AddressType = Literal["Home", "Office", "Other"]


class AddressCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    address_type: AddressType
    full_name: PersonName
    phone_number: str
    address_line_1: LongText
    address_line_2: str | None = None
    city: ShortText
    state: ShortText
    country: ShortText
    postal_code: str
    is_default: bool = False

    @field_validator("address_type", mode="before")
    @classmethod
    def normalize_type(cls, value):
        return value.strip().title() if isinstance(value, str) else value

    @field_validator("phone_number")
    @classmethod
    def check_phone(cls, value: str) -> str:
        return clean_phone(value)

    @field_validator("postal_code")
    @classmethod
    def check_postal_code(cls, value: str) -> str:
        return clean_postal_code(value)

    @field_validator("address_line_2")
    @classmethod
    def check_line_2(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        if len(value) > 255:
            raise ValueError("address_line_2 must not be longer than 255 characters")
        return value or None


class AddressUpdate(AddressCreate):
    is_default: bool | None = None


class AddressOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    address_type: str
    full_name: str
    phone_number: str
    address_line_1: str
    address_line_2: str | None
    city: str
    state: str
    country: str
    postal_code: str
    is_default: bool
    created_at: datetime
    updated_at: datetime
