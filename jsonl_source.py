"""
JSONL Source Implementation

Reads data from JSON Lines (.jsonl) files.
Each line is a complete JSON document.

Author: Mac McAllorum
"""
import json
import logging
from typing import Generator, Tuple, Dict, Any
from data_interfaces import DataSource

logger = logging.getLogger(__name__)


class JSONLSource(DataSource):
    """
    Read records from JSONL file
    
    Expected format (each line):
    {"id": "record_123", "content": {...}}
    
    Or simply:
    {...any json...}  (will generate ID from line number)
    """
    
    def __init__(self, filepath: str, id_field: str = 'id', content_field: str = 'content'):
        """
        Initialize JSONL source
        
        Args:
            filepath: Path to .jsonl file
            id_field: Field name containing record ID (default: 'id')
            content_field: Field name containing record content (default: 'content')
                          If None, entire record is content
        """
        self.filepath = filepath
        self.id_field = id_field
        self.content_field = content_field
        self.file = None
        self.records_read = 0
        
        logger.info(f"JSONLSource initialized: {filepath}")
        logger.info(f"  ID field: {id_field}")
        logger.info(f"  Content field: {content_field if content_field else '(entire record)'}")
    
    def fetch_records(self, query_params: Dict[str, Any] = None) -> Generator[Tuple[str, Any], None, None]:
        """
        Fetch records from JSONL file
        
        Args:
            query_params: Optional dict with 'limit' to limit number of records
            
        Yields:
            Tuple of (record_id, content)
        """
        limit = None
        if query_params:
            limit = query_params.get('limit')
        
        logger.info(f"Reading from JSONL: {self.filepath}")
        if limit:
            logger.info(f"  Limit: {limit} records")
        
        try:
            with open(self.filepath, 'r') as f:
                for line_num, line in enumerate(f, 1):
                    # Check limit
                    if limit and self.records_read >= limit:
                        logger.info(f"Reached limit of {limit} records")
                        break
                    
                    # Skip empty lines
                    line = line.strip()
                    if not line:
                        continue
                    
                    try:
                        # Parse JSON
                        record = json.loads(line)
                        
                        # Extract ID
                        if self.id_field in record:
                            record_id = str(record[self.id_field])
                        else:
                            # Generate ID from line number
                            record_id = f"line_{line_num}"
                        
                        # Extract content
                        if self.content_field and self.content_field in record:
                            content = record[self.content_field]
                        else:
                            # Entire record is content
                            content = record
                        
                        self.records_read += 1
                        yield (record_id, content)
                        
                    except json.JSONDecodeError as e:
                        logger.error(f"Invalid JSON on line {line_num}: {e}")
                        continue
            
            logger.info(f"JSONL fetch completed. Total records read: {self.records_read}")
            
        except FileNotFoundError:
            logger.error(f"JSONL file not found: {self.filepath}")
            raise
        except Exception as e:
            logger.error(f"Error reading JSONL file: {e}")
            raise
    
    def close(self):
        """Close JSONL source"""
        logger.info(f"JSONLSource closed. Total records read: {self.records_read}")


if __name__ == "__main__":
    # Test the JSONL source
    import tempfile
    import os
    
    # Create test JSONL file
    test_file = tempfile.NamedTemporaryFile(suffix='.jsonl', delete=False).name
    
    with open(test_file, 'w') as f:
        f.write('{"id": "rec1", "content": {"name": "Alice", "age": 30}}\n')
        f.write('{"id": "rec2", "content": {"name": "Bob", "age": 25}}\n')
        f.write('{"id": "rec3", "content": {"name": "Charlie", "age": 35}}\n')
    
    try:
        # Test reading
        source = JSONLSource(test_file)
        
        records = list(source.fetch_records())
        print(f"\nRead {len(records)} records:")
        for record_id, content in records:
            print(f"  {record_id}: {content}")
        
        source.close()
        
        # Test with limit
        print("\nWith limit=2:")
        source = JSONLSource(test_file)
        records = list(source.fetch_records({'limit': 2}))
        print(f"Read {len(records)} records")
        source.close()
        
    finally:
        os.unlink(test_file)
