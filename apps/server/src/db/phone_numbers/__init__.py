"""
Phone number database models and services.

This module handles the storage and management of per-user
phone number assignments.
"""

from src.db.phone_numbers.model import UserPhoneNumber
from src.db.phone_numbers.schemas import PhoneNumberCreate, PhoneNumberResponse

__all__ = [
    "UserPhoneNumber",
    "PhoneNumberCreate",
    "PhoneNumberResponse",
]
