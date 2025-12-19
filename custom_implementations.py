"""
Examples of custom data source and sink implementations

This file demonstrates how to extend the pipeline with your own
data sources and sinks.
"""

from data_interfaces import DataSource, DataSink
from typing import Iterator, Tuple, Dict, Any, Optional
import logging
import json

logger = logging.getLogger(__name__)


# ============================================================================
# Example 1: REST API Data Source
# ============================================================================

class RESTAPISource(DataSource):
    """
    Example: Fetch data from a REST API endpoint
    """
    
    def __init__(self, base_url: str, api_key: str, page_size: int = 100):
        self.base_url = base_url
        self.api_key = api_key
        self.page_size = page_size
        logger.info(f"RESTAPISource initialized for {base_url}")
    
    def fetch_records(self, query_params: Optional[Dict[str, Any]] = None) -> Iterator[Tuple[str, str]]:
        """
        Fetch records from paginated REST API
        """
        import requests
        
        page = 1
        total_fetched = 0
        
        while True:
            # Build request
            params = {
                "page": page,
                "page_size": self.page_size
            }
            if query_params:
                params.update(query_params)
            
            headers = {"Authorization": f"Bearer {self.api_key}"}
            
            # Make request
            response = requests.get(self.base_url, params=params, headers=headers)
            response.raise_for_status()
            
            data = response.json()
            records = data.get("results", [])
            
            if not records:
                break
            
            # Yield records
            for record in records:
                record_id = str(record.get("id"))
                content = json.dumps(record)
                yield (record_id, content)
                total_fetched += 1
            
            logger.info(f"Fetched page {page}, total records: {total_fetched}")
            
            # Check if there are more pages
            if not data.get("has_next", False):
                break
            
            page += 1
        
        logger.info(f"REST API fetch completed. Total: {total_fetched}")
    
    def close(self):
        logger.info("RESTAPISource closed")


# ============================================================================
# Example 2: PostgreSQL Data Source
# ============================================================================

class PostgreSQLSource(DataSource):
    """
    Example: Fetch data from PostgreSQL database
    """
    
    def __init__(self, host: str, database: str, user: str, password: str, 
                 table: str, id_column: str = "id", batch_size: int = 1000):
        import psycopg2
        
        self.connection = psycopg2.connect(
            host=host,
            database=database,
            user=user,
            password=password
        )
        self.table = table
        self.id_column = id_column
        self.batch_size = batch_size
        logger.info(f"PostgreSQLSource connected to {host}/{database}")
    
    def fetch_records(self, query_params: Optional[Dict[str, Any]] = None) -> Iterator[Tuple[str, str]]:
        """
        Stream records from PostgreSQL using server-side cursor
        """
        import psycopg2.extras
        
        cursor = self.connection.cursor(
            name='fetch_cursor',
            cursor_factory=psycopg2.extras.RealDictCursor
        )
        
        # Build query with optional filters
        query = f"SELECT * FROM {self.table}"
        if query_params and query_params.get("where"):
            query += f" WHERE {query_params['where']}"
        
        cursor.execute(query)
        
        total_fetched = 0
        while True:
            rows = cursor.fetchmany(self.batch_size)
            if not rows:
                break
            
            for row in rows:
                record_id = str(row[self.id_column])
                content = json.dumps(dict(row), default=str)
                yield (record_id, content)
                total_fetched += 1
            
            logger.info(f"Fetched {len(rows)} rows, total: {total_fetched}")
        
        cursor.close()
        logger.info(f"PostgreSQL fetch completed. Total: {total_fetched}")
    
    def close(self):
        self.connection.close()
        logger.info("PostgreSQLSource closed")


# ============================================================================
# Example 3: S3 Data Sink
# ============================================================================

class S3Sink(DataSink):
    """
    Example: Write data to AWS S3 as JSON Lines
    """
    
    def __init__(self, bucket: str, key_prefix: str, region: str = "us-east-1"):
        import boto3
        
        self.bucket = bucket
        self.key_prefix = key_prefix
        self.s3_client = boto3.client('s3', region_name=region)
        
        self.buffer = []
        self.buffer_size = 1000
        self.batch_num = 0
        
        self.stats = {"inserted": 0, "skipped": 0, "errors": 0}
        self.seen_ids = set()
        
        logger.info(f"S3Sink initialized: s3://{bucket}/{key_prefix}")
    
    def insert_record(self, record_id: str, content: str) -> bool:
        """Buffer records and write to S3 in batches"""
        try:
            if record_id in self.seen_ids:
                self.stats["skipped"] += 1
                return False
            
            self.seen_ids.add(record_id)
            
            record = {"id": record_id, "content": json.loads(content)}
            self.buffer.append(json.dumps(record))
            self.stats["inserted"] += 1
            
            # Flush buffer when full
            if len(self.buffer) >= self.buffer_size:
                self._flush_buffer()
            
            return True
            
        except Exception as e:
            self.stats["errors"] += 1
            logger.error(f"Error buffering record {record_id}: {e}")
            return False
    
    def _flush_buffer(self):
        """Write buffered records to S3"""
        if not self.buffer:
            return
        
        self.batch_num += 1
        key = f"{self.key_prefix}/batch_{self.batch_num:05d}.jsonl"
        
        content = "\n".join(self.buffer) + "\n"
        
        self.s3_client.put_object(
            Bucket=self.bucket,
            Key=key,
            Body=content.encode('utf-8'),
            ContentType='application/x-ndjson'
        )
        
        logger.info(f"Flushed {len(self.buffer)} records to s3://{self.bucket}/{key}")
        self.buffer = []
    
    def commit(self):
        """Flush any remaining buffered records"""
        self._flush_buffer()
        logger.info(f"S3Sink committed. Stats: {self.stats}")
    
    def close(self):
        self.commit()
        logger.info(f"S3Sink closed. Total batches: {self.batch_num}")
    
    def get_stats(self) -> Dict[str, int]:
        return self.stats.copy()


# ============================================================================
# Example 4: MongoDB Sink
# ============================================================================

class MongoDBSink(DataSink):
    """
    Example: Write data to MongoDB collection
    """
    
    def __init__(self, connection_string: str, database: str, collection: str):
        from pymongo import MongoClient
        
        self.client = MongoClient(connection_string)
        self.db = self.client[database]
        self.collection = self.db[collection]
        
        self.stats = {"inserted": 0, "skipped": 0, "errors": 0}
        
        logger.info(f"MongoDBSink initialized: {database}.{collection}")
    
    def insert_record(self, record_id: str, content: str) -> bool:
        """Insert record into MongoDB with upsert to handle duplicates"""
        try:
            document = json.loads(content)
            document["_id"] = record_id
            
            result = self.collection.replace_one(
                {"_id": record_id},
                document,
                upsert=True
            )
            
            if result.upserted_id:
                self.stats["inserted"] += 1
                return True
            else:
                self.stats["skipped"] += 1  # Was an update
                return False
            
        except Exception as e:
            self.stats["errors"] += 1
            logger.error(f"Error inserting record {record_id}: {e}")
            return False
    
    def commit(self):
        """MongoDB auto-commits, but we log stats"""
        logger.info(f"MongoDBSink commit. Stats: {self.stats}")
    
    def close(self):
        self.client.close()
        logger.info(f"MongoDBSink closed. Final stats: {self.stats}")
    
    def get_stats(self) -> Dict[str, int]:
        return self.stats.copy()


# ============================================================================
# Example 5: Kafka Data Sink
# ============================================================================

class KafkaSink(DataSink):
    """
    Example: Write data to Kafka topic
    """
    
    def __init__(self, bootstrap_servers: str, topic: str):
        from kafka import KafkaProducer
        
        self.producer = KafkaProducer(
            bootstrap_servers=bootstrap_servers,
            value_serializer=lambda v: json.dumps(v).encode('utf-8')
        )
        self.topic = topic
        self.stats = {"inserted": 0, "skipped": 0, "errors": 0}
        
        logger.info(f"KafkaSink initialized: {topic} on {bootstrap_servers}")
    
    def insert_record(self, record_id: str, content: str) -> bool:
        """Send record to Kafka topic"""
        try:
            message = {
                "id": record_id,
                "content": json.loads(content),
                "timestamp": None  # Kafka will add timestamp
            }
            
            self.producer.send(self.topic, value=message, key=record_id.encode('utf-8'))
            self.stats["inserted"] += 1
            return True
            
        except Exception as e:
            self.stats["errors"] += 1
            logger.error(f"Error sending record {record_id} to Kafka: {e}")
            return False
    
    def commit(self):
        """Flush producer to ensure all messages are sent"""
        self.producer.flush()
        logger.info(f"KafkaSink flushed. Stats: {self.stats}")
    
    def close(self):
        self.commit()
        self.producer.close()
        logger.info(f"KafkaSink closed. Final stats: {self.stats}")
    
    def get_stats(self) -> Dict[str, int]:
        return self.stats.copy()


# ============================================================================
# Usage Example
# ============================================================================

if __name__ == "__main__":
    """
    Example showing how to use custom implementations
    """
    from pipeline import DataPipeline
    
    # Example: PostgreSQL → S3
    # source = PostgreSQLSource(
    #     host="localhost",
    #     database="mydb",
    #     user="user",
    #     password="password",
    #     table="transactions"
    # )
    # 
    # sink = S3Sink(
    #     bucket="my-data-bucket",
    #     key_prefix="exports/transactions"
    # )
    # 
    # pipeline = DataPipeline(source, sink, num_threads=1)
    # stats = pipeline.run()
    # pipeline.cleanup()
    
    print("See code for usage examples")
    print("Uncomment the relevant section and provide your credentials")
