"""Verify dynamorator package can be imported correctly."""

try:
    from dynamorator import DynamoDBStore, DateTimeEncoder
    print("✓ Successfully imported DynamoDBStore")
    print("✓ Successfully imported DateTimeEncoder")
    
    # Test disabled mode (no AWS credentials needed)
    store = DynamoDBStore(table_name=None)
    print(f"✓ Created disabled store: is_enabled={store.is_enabled()}")
    
    # Test DateTimeEncoder
    from datetime import datetime
    import json
    data = {"time": datetime.now()}
    encoded = json.dumps(data, cls=DateTimeEncoder)
    print(f"✓ DateTimeEncoder works: {encoded[:50]}...")
    
    print("\n✅ All basic checks passed!")
    print("\nTo test with AWS:")
    print("  store = DynamoDBStore(table_name='test-table')")
    print("  store.put('key', {'data': 'value'}, ttl_days=1)")
    print("  print(store.get('key'))")
    
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
