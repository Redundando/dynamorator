import json
import time
from typing import Optional, Dict
import boto3
from botocore.exceptions import ClientError
from logorator import Logger
from .encoder import DateTimeEncoder


class DynamoDBStore:
    """Lightweight DynamoDB JSON storage with automatic TTL support."""
    
    _clients = {}
    _table_exists_cache = {}
    
    def __init__(self, table_name: Optional[str] = None, silent: bool = False):
        self.table_name = table_name
        self.silent = silent
        self._client = None
        
        if self.is_enabled():
            self._client = self._get_client()
            self._ensure_table_exists()
    
    def __str__(self):
        return f"DynamoDBStore(table_name={self.table_name})"
    
    @classmethod
    def _get_client(cls):
        """Get or create shared boto3 DynamoDB client."""
        if 'dynamodb' not in cls._clients:
            cls._clients['dynamodb'] = boto3.client('dynamodb')
        return cls._clients['dynamodb']
    
    def is_enabled(self) -> bool:
        """Returns True if table_name is set and boto3 is available."""
        return self.table_name is not None
    
    def _ensure_table_exists(self):
        """Create table if it doesn't exist and enable TTL."""
        if self.table_name in self._table_exists_cache:
            return
        
        try:
            self._client.describe_table(TableName=self.table_name)
            self._table_exists_cache[self.table_name] = True
        except ClientError as e:
            if e.response['Error']['Code'] == 'ResourceNotFoundException':
                self._create_table()
            else:
                raise
    
    def _create_table(self):
        """Create DynamoDB table with TTL enabled."""
        @Logger(silent=self.silent, override_function_name="create_table")
        def _create(self):
            Logger.note(f"Creating DynamoDB table: {self.table_name}")
            
            self._client.create_table(
                TableName=self.table_name,
                KeySchema=[
                    {'AttributeName': 'cache_id', 'KeyType': 'HASH'}
                ],
                AttributeDefinitions=[
                    {'AttributeName': 'cache_id', 'AttributeType': 'S'}
                ],
                BillingMode='PAY_PER_REQUEST'
            )
            
            Logger.note(f"Waiting for table to be ready: {self.table_name}")
            waiter = self._client.get_waiter('table_exists')
            waiter.wait(TableName=self.table_name)
            
            Logger.note(f"Enabling TTL on table: {self.table_name}")
            self._client.update_time_to_live(
                TableName=self.table_name,
                TimeToLiveSpecification={
                    'Enabled': True,
                    'AttributeName': 'ttl'
                }
            )
            
            Logger.note(f"Table ready: {self.table_name}")
            self._table_exists_cache[self.table_name] = True
        
        _create(self)
    
    def get(self, key: str) -> Optional[dict]:
        """Retrieve JSON data by key. Returns None if not found or on error."""
        @Logger(include_args=["self", "key"], silent=self.silent, override_function_name="get")
        def _get(self, key):
            if not self.is_enabled():
                return None
            
            try:
                response = self._client.get_item(
                    TableName=self.table_name,
                    Key={'cache_id': {'S': key}}
                )
                
                if 'Item' not in response:
                    return None
                
                data_str = response['Item'].get('data', {}).get('S')
                if data_str:
                    return json.loads(data_str)
                return None
            except Exception:
                return None
        
        return _get(self, key)
    
    def put(self, key: str, data: dict, ttl_days: float):
        """Store JSON data with TTL. Silent error handling."""
        @Logger(exclude_args=["data", "ttl_days"], silent=self.silent, override_function_name="put")
        def _put(self, key, data, ttl_days):
            if not self.is_enabled():
                return
            
            try:
                now = int(time.time())
                ttl = now + int(ttl_days * 86400)
                
                self._client.put_item(
                    TableName=self.table_name,
                    Item={
                        'cache_id': {'S': key},
                        'data': {'S': json.dumps(data, cls=DateTimeEncoder)},
                        'ttl': {'N': str(ttl)},
                        'created_at': {'N': str(now)}
                    }
                )
            except Exception:
                pass
        
        _put(self, key, data, ttl_days)
    
    def delete(self, key: str):
        """Delete entry by key. Silent error handling."""
        @Logger(include_args=["self", "key"], silent=self.silent, override_function_name="delete")
        def _delete(self, key):
            if not self.is_enabled():
                return
            
            try:
                self._client.delete_item(
                    TableName=self.table_name,
                    Key={'cache_id': {'S': key}}
                )
            except Exception:
                pass
        
        _delete(self, key)
    
    def list_keys(self, limit: int = 100, last_key: Optional[str] = None) -> Dict:
        """List all keys in table. Returns {'keys': [...], 'last_key': ...}"""
        @Logger(exclude_args=["limit", "last_key"], silent=self.silent, override_function_name="list_keys")
        def _list_keys(self, limit, last_key):
            if not self.is_enabled():
                return {'keys': [], 'last_key': None}
            
            try:
                params = {
                    'TableName': self.table_name,
                    'ProjectionExpression': 'cache_id',
                    'Limit': limit
                }
                
                if last_key:
                    params['ExclusiveStartKey'] = {'cache_id': {'S': last_key}}
                
                response = self._client.scan(**params)
                
                keys = [item['cache_id']['S'] for item in response.get('Items', [])]
                next_key = None
                
                if 'LastEvaluatedKey' in response:
                    next_key = response['LastEvaluatedKey']['cache_id']['S']
                
                return {'keys': keys, 'last_key': next_key}
            except Exception:
                return {'keys': [], 'last_key': None}
        
        return _list_keys(self, limit, last_key)
