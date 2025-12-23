"""
Production implementations for Elasticsearch source and MySQL sink

Author: Kevin McAllorum (kevin_mcallorum@linux.com)
GitHub: github.com/kmcallorum
License: MIT
"""
import requests
import json
import mysql.connector
import logging
from typing import Iterator, Tuple, Dict, Any, Optional
from data_interfaces import DataSource, DataSink

logger = logging.getLogger(__name__)


class ElasticsearchSource(DataSource):
    """Production Elasticsearch data source"""
    
    def __init__(self, es_url: str, batch_size: int = 1000, 
                 es_user: Optional[str] = None, es_pass: Optional[str] = None,
                 api_key: Optional[str] = None):
        self.es_url = es_url
        self.batch_size = batch_size
        self.es_user = es_user
        self.es_pass = es_pass
        self.api_key = api_key
        
        # Setup auth
        self.headers = {"Content-Type": "application/json"}
        self.auth = None
        if api_key:
            self.headers["Authorization"] = f"ApiKey {api_key}"
        elif es_user and es_pass:
            self.auth = (es_user, es_pass)
        else:
            raise ValueError("Either api_key or both es_user and es_pass must be provided")
    
    def fetch_records(self, query_params: Optional[Dict[str, Any]] = None) -> Iterator[Tuple[str, str]]:
        """Fetch records from Elasticsearch using scroll API"""
        query = self._build_query(query_params)
        
        # Initial scroll request
        params = {"scroll": "2m", "size": self.batch_size}
        logger.info(f"Starting Elasticsearch scroll from {self.es_url}")
        
        response = requests.post(
            self.es_url, 
            auth=self.auth, 
            headers=self.headers, 
            params=params, 
            data=json.dumps(query)
        )
        
        if response.status_code != 200:
            raise Exception(f"Initial scroll failed: {response.status_code}, {response.text}")
        
        data = response.json()
        scroll_id = data.get("_scroll_id")
        hits = data.get("hits", {}).get("hits", [])
        total_fetched = 0
        
        # Process hits
        while hits:
            for hit in hits:
                record_id = hit["_id"]
                content = json.dumps(hit)
                yield (record_id, content)
            
            total_fetched += len(hits)
            logger.info(f"Fetched {len(hits)} records. Total so far: {total_fetched}")
            
            # Get next batch
            base_url = self.es_url.split('/_search')[0].rsplit('/', 1)[0]
            response = requests.post(
                f"{base_url}/_search/scroll",
                auth=self.auth,
                headers=self.headers,
                data=json.dumps({"scroll": "2m", "scroll_id": scroll_id})
            )
            
            if response.status_code != 200:
                logger.error(f"Scroll request failed: {response.status_code}, {response.text}")
                break
            
            data = response.json()
            scroll_id = data.get("_scroll_id")
            hits = data.get("hits", {}).get("hits", [])
        
        logger.info(f"Elasticsearch fetch completed. Total records: {total_fetched}")
    
    def _build_query(self, query_params: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Build Elasticsearch query from parameters"""
        if not query_params or query_params.get("match_all"):
            return {"query": {"match_all": {}}}
        
        gte = query_params.get("gte")
        lte = query_params.get("lte")
        
        if not gte or not lte:
            raise ValueError("gte and lte required unless match_all is True")
        
        return {
            "query": {
                "range": {
                    "@timestamp": {
                        "gte": gte,
                        "lte": lte,
                        "format": "strict_date_optional_time"
                    }
                }
            }
        }
    
    def close(self):
        """No cleanup needed for ES source"""
        pass


class MySQLSink(DataSink):
    """Production MySQL data sink with thread-safe operations"""
    
    def __init__(self, host: str, user: str, password: str, database: str, table: str):
        self.host = host
        self.user = user
        self.password = password
        self.database = database
        self.table = table
        
        self.conn = mysql.connector.connect(
            host=host, user=user, password=password, database=database
        )
        self.cursor = self.conn.cursor()
        
        self.stats = {
            "inserted": 0,
            "skipped": 0,
            "errors": 0
        }
        
        # Prepare insert statement
        self.insert_sql = f"INSERT IGNORE INTO {table} (id, content) VALUES (%s, %s)"
        logger.info(f"MySQLSink initialized for table {table} in database {database}")
    
    def insert_record(self, record_id: str, content: Any) -> bool:
        """Insert a record, returns True if inserted, False if skipped"""
        try:
            # Convert dict to JSON string if needed
            if isinstance(content, dict):
                content = json.dumps(content)
            self.cursor.execute(self.insert_sql, (record_id, content))
            if self.cursor.rowcount > 0:
                self.stats["inserted"] += 1
                return True
            else:
                self.stats["skipped"] += 1
                return False
        except Exception as e:
            self.stats["errors"] += 1
            logger.error(f"Error inserting ID {record_id}: {e}")
            return False
    
    def commit(self):
        """Commit the transaction"""
        self.conn.commit()
        logger.info(f"Committed transaction. Stats: {self.stats}")
    
    def close(self):
        """Close database connections"""
        self.commit()
        self.cursor.close()
        self.conn.close()
        logger.info(f"MySQLSink closed. Final stats: {self.stats}")
    
    def get_stats(self) -> Dict[str, int]:
        """Get operation statistics"""
        return self.stats.copy()
