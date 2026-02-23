import json
import time
import gzip
import base64
from typing import Optional, Dict
import boto3
from botocore.exceptions import ClientError
from logorator import Logger
from .encoder import DateTimeEncoder


class DynamoDBStore:
    """Lightweight DynamoDB JSON storage with automatic TTL support."""
    
    # DynamoDB attribute names
    PARTITION_KEY = 'cache_id'
    DATA_ATTR = 'data'
    TTL_ATTR = 'ttl'
    CREATED_AT_ATTR = 'created_at'
    COMPRESSED_ATTR = 'compressed'
    
    # Batch operation limits
    BATCH_GET_SIZE = 100
    BATCH_GET_MAX_KEYS = 10000
    BATCH_GET_MAX_RETRIES = 5
    BATCH_GET_INITIAL_DELAY = 0.5
    
    # Time constants
    SECONDS_PER_DAY = 86400
    
    # Default limits
    DEFAULT_LIST_LIMIT = 100
    
    # Compression settings
    DEFAULT_COMPRESS_THRESHOLD = 1024
    
    _clients = {}
    _table_exists_cache = {}
    
    def __init__(self, table_name: Optional[str] = None, silent: bool = False, compress: bool = False, compress_threshold: int = None):
        self.table_name = table_name
        self.silent = silent
        self.compress = compress
        self.compress_threshold = compress_threshold or self.DEFAULT_COMPRESS_THRESHOLD
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
                    {'AttributeName': self.PARTITION_KEY, 'KeyType': 'HASH'}
                ],
                AttributeDefinitions=[
                    {'AttributeName': self.PARTITION_KEY, 'AttributeType': 'S'}
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
                    'AttributeName': self.TTL_ATTR
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
                    Key={self.PARTITION_KEY: {'S': key}}
                )
                
                if 'Item' not in response:
                    return None
                
                item = response['Item']
                data_str = item.get(self.DATA_ATTR, {}).get('S')
                if data_str:
                    is_compressed = item.get(self.COMPRESSED_ATTR, {}).get('BOOL', False)
                    if is_compressed:
                        data_str = gzip.decompress(base64.b64decode(data_str)).decode('utf-8')
                    return json.loads(data_str)
                return None
            except Exception:
                return None
        
        return _get(self, key)
    
    def batch_get(self, keys: list[str]) -> dict[str, dict]:
        """Retrieve multiple items by keys. Returns dict mapping found keys to their data."""
        @Logger(exclude_args=["keys"], silent=self.silent, override_function_name="batch_get")
        def _batch_get(self, keys):
            if not self.is_enabled() or not keys:
                return {}
            
            if len(keys) > self.BATCH_GET_MAX_KEYS:
                keys = keys[:self.BATCH_GET_MAX_KEYS]
            
            result = {}
            
            try:
                for i in range(0, len(keys), self.BATCH_GET_SIZE):
                    batch = keys[i:i+self.BATCH_GET_SIZE]
                    request_items = {
                        self.table_name: {
                            'Keys': [{self.PARTITION_KEY: {'S': k}} for k in batch]
                        }
                    }
                    
                    unprocessed = request_items
                    delay = self.BATCH_GET_INITIAL_DELAY
                    
                    for attempt in range(self.BATCH_GET_MAX_RETRIES):
                        if not unprocessed:
                            break
                        
                        response = self._client.batch_get_item(RequestItems=unprocessed)
                        
                        for item in response.get('Responses', {}).get(self.table_name, []):
                            key = item[self.PARTITION_KEY]['S']
                            data_str = item.get(self.DATA_ATTR, {}).get('S')
                            if data_str:
                                is_compressed = item.get(self.COMPRESSED_ATTR, {}).get('BOOL', False)
                                if is_compressed:
                                    data_str = gzip.decompress(base64.b64decode(data_str)).decode('utf-8')
                                result[key] = json.loads(data_str)
                        
                        unprocessed = response.get('UnprocessedKeys')
                        if unprocessed:
                            time.sleep(delay)
                            delay *= 2
                
                return result
            except Exception:
                return {}
        
        return _batch_get(self, keys)
    
    def put(self, key: str, data: dict, ttl_days: float):
        """Store JSON data with TTL. Silent error handling."""
        @Logger(exclude_args=["data", "ttl_days"], silent=self.silent, override_function_name="put")
        def _put(self, key, data, ttl_days):
            if not self.is_enabled():
                return
            
            try:
                now = int(time.time())
                ttl = now + int(ttl_days * self.SECONDS_PER_DAY)
                
                json_str = json.dumps(data, cls=DateTimeEncoder)
                is_compressed = False
                
                if self.compress and len(json_str) > self.compress_threshold:
                    json_str = base64.b64encode(gzip.compress(json_str.encode('utf-8'))).decode('utf-8')
                    is_compressed = True
                
                item = {
                    self.PARTITION_KEY: {'S': key},
                    self.DATA_ATTR: {'S': json_str},
                    self.TTL_ATTR: {'N': str(ttl)},
                    self.CREATED_AT_ATTR: {'N': str(now)}
                }
                
                if is_compressed:
                    item[self.COMPRESSED_ATTR] = {'BOOL': True}
                
                self._client.put_item(TableName=self.table_name, Item=item)
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
                    Key={self.PARTITION_KEY: {'S': key}}
                )
            except Exception:
                pass
        
        _delete(self, key)
    
    def list_keys(self, limit: int = None, last_key: Optional[str] = None) -> Dict:
        """List all keys in table. Returns {'keys': [...], 'last_key': ...}"""
        @Logger(exclude_args=["limit", "last_key"], silent=self.silent, override_function_name="list_keys")
        def _list_keys(self, limit, last_key):
            if not self.is_enabled():
                return {'keys': [], 'last_key': None}
            
            try:
                params = {
                    'TableName': self.table_name,
                    'ProjectionExpression': self.PARTITION_KEY,
                    'Limit': limit or self.DEFAULT_LIST_LIMIT
                }
                
                if last_key:
                    params['ExclusiveStartKey'] = {self.PARTITION_KEY: {'S': last_key}}
                
                response = self._client.scan(**params)
                
                keys = [item[self.PARTITION_KEY]['S'] for item in response.get('Items', [])]
                next_key = None
                
                if 'LastEvaluatedKey' in response:
                    next_key = response['LastEvaluatedKey'][self.PARTITION_KEY]['S']
                
                return {'keys': keys, 'last_key': next_key}
            except Exception:
                return {'keys': [], 'last_key': None}
        
        return _list_keys(self, limit, last_key)
