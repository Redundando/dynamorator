"""Example usage of dynamorator package."""

from datetime import datetime
from dynamorator import DynamoDBStore

# Initialize store (will create table if it doesn't exist)
store = DynamoDBStore(table_name="dynamorator-example")

# Example 1: Basic storage
print("Example 1: Basic storage")
store.put("user:alice", {"name": "Alice", "age": 30}, ttl_days=7)
data = store.get("user:alice")
print(f"Retrieved: {data}")

# Example 2: Datetime handling
print("\nExample 2: Datetime handling")
store.put("event:meeting", {
    "title": "Team Sync",
    "scheduled": datetime(2026, 3, 15, 14, 30),
    "created": datetime.now()
}, ttl_days=30)
event = store.get("event:meeting")
print(f"Event: {event}")

# Example 3: List keys
print("\nExample 3: List keys")
result = store.list_keys(limit=10)
print(f"Keys: {result['keys']}")
print(f"Has more: {result['last_key'] is not None}")

# Example 4: Delete
print("\nExample 4: Delete")
store.delete("user:alice")
deleted = store.get("user:alice")
print(f"After delete: {deleted}")

# Example 5: Disabled mode
print("\nExample 5: Disabled mode")
disabled_store = DynamoDBStore(table_name=None)
print(f"Is enabled: {disabled_store.is_enabled()}")
disabled_store.put("key", {"data": 1}, ttl_days=1)  # No-op
print(f"Get from disabled: {disabled_store.get('key')}")  # Returns None
