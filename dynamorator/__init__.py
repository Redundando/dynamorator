"""Lightweight DynamoDB JSON storage with automatic TTL support."""

from .store import DynamoDBStore
from .encoder import DateTimeEncoder

__version__ = "0.1.3"
__all__ = ["DynamoDBStore", "DateTimeEncoder"]
