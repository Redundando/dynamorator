"""Tests for dynamorator package."""

import pytest
from dynamorator import DynamoDBStore, DateTimeEncoder


def test_store_disabled_when_no_table_name():
    """Test that store is disabled when table_name is None."""
    store = DynamoDBStore(table_name=None)
    assert not store.is_enabled()
    assert store.get("key") is None


def test_datetime_encoder():
    """Test DateTimeEncoder handles datetime objects."""
    from datetime import datetime
    import json
    
    data = {"timestamp": datetime(2026, 1, 1, 12, 0, 0)}
    result = json.dumps(data, cls=DateTimeEncoder)
    assert "2026-01-01T12:00:00" in result


# TODO: Add integration tests with mocked boto3 client
# TODO: Add tests for put, get, delete operations
# TODO: Add tests for list_keys pagination
# TODO: Add tests for table creation
