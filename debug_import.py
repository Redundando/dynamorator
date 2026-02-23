"""Simple test to explore the import issue."""

import sys
print("Python path:")
for p in sys.path:
    print(f"  {p}")

print("\nImporting dynamorator...")
from dynamorator import DynamoDBStore

print(f"\nDynamoDBStore location: {DynamoDBStore.__module__}")
print(f"File: {DynamoDBStore.__init__.__code__.co_filename}")

print("\nChecking __init__ signature:")
import inspect
sig = inspect.signature(DynamoDBStore.__init__)
print(f"Parameters: {sig}")

print("\nChecking for batch_get method:")
print(f"Has batch_get: {hasattr(DynamoDBStore, 'batch_get')}")

print("\nChecking for compress attribute:")
store = DynamoDBStore(table_name=None)
print(f"Has compress: {hasattr(store, 'compress')}")

print("\nAll methods:")
for attr in dir(store):
    if not attr.startswith('_'):
        print(f"  {attr}")
