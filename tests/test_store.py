"""Tests for dynamorator package."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
import os
from datetime import datetime
from dynamorator import DynamoDBStore, DateTimeEncoder


def test_store_disabled_when_no_table_name():
    """Test that store is disabled when table_name is None."""
    store = DynamoDBStore(table_name=None)
    assert not store.is_enabled()
    assert store.get("key") is None


def test_datetime_encoder():
    """Test DateTimeEncoder handles datetime objects."""
    import json
    
    data = {"timestamp": datetime(2026, 1, 1, 12, 0, 0)}
    result = json.dumps(data, cls=DateTimeEncoder)
    assert "2026-01-01T12:00:00" in result


@pytest.fixture
def test_table_name():
    """Generate unique test table name."""
    return f"dynamorator-test-{os.getpid()}"


@pytest.fixture
def store(test_table_name):
    """Create test store instance."""
    store = DynamoDBStore(table_name=test_table_name, silent=True)
    yield store
    # Cleanup: delete all test items
    result = store.list_keys(limit=1000)
    for key in result['keys']:
        store.delete(key)


@pytest.fixture
def compressed_store(test_table_name):
    """Create test store with compression enabled."""
    table_name = f"{test_table_name}-compressed"
    store = DynamoDBStore(table_name=table_name, silent=True, compress=True, compress_threshold=100)
    yield store
    # Cleanup
    result = store.list_keys(limit=1000)
    for key in result['keys']:
        store.delete(key)


class TestBasicOperations:
    """Test basic CRUD operations."""
    
    def test_put_and_get(self, store):
        """Test storing and retrieving data."""
        data = {"name": "Alice", "score": 100}
        store.put("user:1", data, ttl_days=1)
        result = store.get("user:1")
        assert result == data
    
    def test_get_nonexistent_key(self, store):
        """Test getting a key that doesn't exist."""
        result = store.get("nonexistent")
        assert result is None
    
    def test_delete(self, store):
        """Test deleting data."""
        store.put("user:2", {"name": "Bob"}, ttl_days=1)
        store.delete("user:2")
        result = store.get("user:2")
        assert result is None
    
    def test_datetime_serialization(self, store):
        """Test automatic datetime serialization."""
        data = {
            "created": datetime(2026, 3, 15, 14, 30),
            "name": "Event"
        }
        store.put("event:1", data, ttl_days=1)
        result = store.get("event:1")
        assert result["name"] == "Event"
        assert "2026-03-15T14:30:00" in result["created"]


class TestBatchOperations:
    """Test batch_get functionality."""
    
    def test_batch_get_multiple_keys(self, store):
        """Test retrieving multiple items at once."""
        # Store multiple items
        for i in range(5):
            store.put(f"item:{i}", {"id": i, "value": f"data_{i}"}, ttl_days=1)
        
        # Batch get
        keys = [f"item:{i}" for i in range(5)]
        result = store.batch_get(keys)
        
        assert len(result) == 5
        assert result["item:0"]["id"] == 0
        assert result["item:4"]["value"] == "data_4"
    
    def test_batch_get_missing_keys(self, store):
        """Test batch_get with some missing keys."""
        store.put("exists:1", {"data": "here"}, ttl_days=1)
        
        keys = ["exists:1", "missing:1", "missing:2"]
        result = store.batch_get(keys)
        
        assert len(result) == 1
        assert "exists:1" in result
        assert "missing:1" not in result
    
    def test_batch_get_empty_list(self, store):
        """Test batch_get with empty key list."""
        result = store.batch_get([])
        assert result == {}
    
    def test_batch_get_large_batch(self, store):
        """Test batch_get with more than 100 items."""
        # Store 150 items
        for i in range(150):
            store.put(f"large:{i}", {"id": i}, ttl_days=1)
        
        keys = [f"large:{i}" for i in range(150)]
        result = store.batch_get(keys)
        
        assert len(result) == 150


class TestListKeys:
    """Test list_keys functionality."""
    
    def test_list_keys(self, store):
        """Test listing keys in table."""
        # Store some items
        for i in range(5):
            store.put(f"list:{i}", {"id": i}, ttl_days=1)
        
        result = store.list_keys(limit=10)
        assert len(result['keys']) >= 5
        assert any(k.startswith("list:") for k in result['keys'])
    
    def test_list_keys_pagination(self, store):
        """Test pagination with list_keys."""
        # Store items
        for i in range(10):
            store.put(f"page:{i}", {"id": i}, ttl_days=1)
        
        # Get first page
        result = store.list_keys(limit=5)
        assert len(result['keys']) <= 5


class TestCompression:
    """Test compression functionality."""
    
    def test_compression_small_item(self, compressed_store):
        """Test that small items are not compressed."""
        small_data = {"key": "value"}
        compressed_store.put("small:1", small_data, ttl_days=1)
        result = compressed_store.get("small:1")
        assert result == small_data
    
    def test_compression_large_item(self, compressed_store):
        """Test that large items are compressed and decompressed correctly."""
        # Create data larger than threshold (100 bytes)
        large_data = {"data": "x" * 200, "id": 123, "nested": {"field": "value" * 10}}
        compressed_store.put("large:1", large_data, ttl_days=1)
        result = compressed_store.get("large:1")
        assert result == large_data
    
    def test_compression_with_batch_get(self, compressed_store):
        """Test batch_get works with compressed items."""
        # Store mix of small and large items
        compressed_store.put("small:1", {"data": "tiny"}, ttl_days=1)
        compressed_store.put("large:1", {"data": "x" * 200}, ttl_days=1)
        
        result = compressed_store.batch_get(["small:1", "large:1"])
        
        assert len(result) == 2
        assert result["small:1"]["data"] == "tiny"
        assert result["large:1"]["data"] == "x" * 200
    
    def test_compression_disabled_by_default(self, store):
        """Test that compression is disabled by default."""
        assert store.compress is False
        large_data = {"data": "x" * 1000}
        store.put("nocompress:1", large_data, ttl_days=1)
        result = store.get("nocompress:1")
        assert result == large_data
    
    def test_custom_compression_threshold(self, test_table_name):
        """Test custom compression threshold."""
        store = DynamoDBStore(
            table_name=f"{test_table_name}-custom",
            silent=True,
            compress=True,
            compress_threshold=500
        )
        
        # Data under threshold
        small_data = {"data": "x" * 100}
        store.put("under:1", small_data, ttl_days=1)
        result = store.get("under:1")
        assert result == small_data
        
        # Data over threshold
        large_data = {"data": "x" * 600}
        store.put("over:1", large_data, ttl_days=1)
        result = store.get("over:1")
        assert result == large_data
        
        # Cleanup
        store.delete("under:1")
        store.delete("over:1")
