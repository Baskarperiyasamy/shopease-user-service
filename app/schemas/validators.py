import re
from typing import Annotated

from pydantic import StringConstraints

PHONE_PATTERN = re.compile(r"^\+?[0-9]{10,15}$")
POSTAL_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9 \-]{2,9}$")

PersonName = Annotated[str, StringConstraints(strip_whitespace=True, min_length=2, max_length=100)]
ShortText = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)]
LongText = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=255)]


def clean_phone(value: str) -> str:
    cleaned = re.sub(r"[\s\-()]", "", value)
    if not PHONE_PATTERN.match(cleaned):
        raise ValueError("Phone number must have 10 to 15 digits and may start with +")
    return cleaned


def clean_postal_code(value: str) -> str:
    value = value.strip()
    if not POSTAL_PATTERN.match(value):
        raise ValueError("Postal code must be 3 to 10 letters, digits, spaces or hyphens")
    return value
