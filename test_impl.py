"""
Test implementations for file-based data source and sink

Author: Kevin McAllorum (kevin_mcallorum@linux.com)
GitHub: github.com/kmcallorum
License: MIT
"""
import csv
import json
import logging
from typing import Iterator, Tuple, Dict, Any, Optional
from data_interfaces import DataSource, DataSink

logger = logging.getLogger(__name__)


class CSVSource(DataSource):
    """Test data source that reads from CSV file"""
    
    def __init__(self, filepath: str, id_column: str = "id", content_column: str = "content"):
        """
        Args:
            filepath: Path to CSV file
            id_column: Name of column containing record IDs
            content_column: Name of column containing JSON content (or will be converted to JSON)
        """
        self.filepath = filepath
        self.id_column = id_column
        self.content_column = content_column
        self.total_read = 0
    
    def fetch_records(self, query_params: Optional[Dict[str, Any]] = None) -> Iterator[Tuple[str, str]]:
        """
        Read records from CSV file.
        Query params can include 'limit' for testing with smaller datasets.
        """
        limit = query_params.get("limit") if query_params else None
        
        logger.info(f"Reading from CSV: {self.filepath}")
        
        with open(self.filepath, 'r', newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            
            for i, row in enumerate(reader):
                if limit and i >= limit:
                    break
                
                record_id = row.get(self.id_column)
                content = row.get(self.content_column)
                
                if not record_id:
                    logger.warning(f"Row {i} missing ID column '{self.id_column}', skipping")
                    continue
                
                # If content is not JSON, convert the entire row to JSON
                if content and self._is_json(content):
                    json_content = content
                else:
                    json_content = json.dumps(row)
                
                self.total_read += 1
                yield (record_id, json_content)
        
        logger.info(f"CSV fetch completed. Total records read: {self.total_read}")
    
    def _is_json(self, text: str) -> bool:
        """Check if text is valid JSON"""
        try:
            json.loads(text)
            return True
        except (json.JSONDecodeError, ValueError, TypeError):
            return False
    
    def close(self):
        """No cleanup needed for CSV source"""
        logger.info(f"CSVSource closed. Total records read: {self.total_read}")


class FileSink(DataSink):
    """Test data sink that writes to a text file"""
    
    def __init__(self, filepath: str, mode: str = "w"):
        """
        Args:
            filepath: Path to output file
            mode: File open mode ('w' to overwrite, 'a' to append)
        """
        self.filepath = filepath
        self.file = open(filepath, mode, encoding='utf-8')
        self.stats = {
            "inserted": 0,
            "skipped": 0,
            "errors": 0
        }
        self.seen_ids = set()  # Track duplicates
        logger.info(f"FileSink initialized: {filepath}")
    
    def insert_record(self, record_id: str, content: str) -> bool:
        """Write record to file, one per line as JSON"""
        try:
            # Check for duplicates
            if record_id in self.seen_ids:
                self.stats["skipped"] += 1
                logger.debug(f"Skipping duplicate ID: {record_id}")
                return False
            
            self.seen_ids.add(record_id)
            
            # Write as JSON line
            record = {
                "id": record_id,
                "content": json.loads(content) if self._is_json(content) else content
            }
            self.file.write(json.dumps(record) + "\n")
            self.stats["inserted"] += 1
            
            # Log progress periodically
            if self.stats["inserted"] % 100 == 0:
                logger.info(f"FileSink progress: {self.stats['inserted']} records written")
            
            return True
            
        except Exception as e:
            self.stats["errors"] += 1
            logger.error(f"Error writing ID {record_id}: {e}")
            return False
    
    def _is_json(self, text: str) -> bool:
        """Check if text is valid JSON"""
        try:
            json.loads(text)
            return True
        except (json.JSONDecodeError, ValueError, TypeError):
            return False
    
    def commit(self):
        """Flush the file buffer"""
        self.file.flush()
        logger.info(f"FileSink committed. Stats: {self.stats}")
    
    def close(self):
        """Close the file"""
        self.commit()
        self.file.close()
        logger.info(f"FileSink closed. Final stats: {self.stats}")
    
    def get_stats(self) -> Dict[str, int]:
        """Get operation statistics"""
        return self.stats.copy()


class JSONLSink(DataSink):
    """Alternative test sink that writes records as JSON Lines (one JSON object per line)"""
    
    def __init__(self, filepath: str, mode: str = "w"):
        self.filepath = filepath
        self.file = open(filepath, mode, encoding='utf-8')
        self.stats = {"inserted": 0, "skipped": 0, "errors": 0}
        self.seen_ids = set()
        logger.info(f"JSONLSink initialized: {filepath}")
    
    def insert_record(self, record_id: str, content: str) -> bool:
        """Write record as a single JSON line"""
        try:
            if record_id in self.seen_ids:
                self.stats["skipped"] += 1
                return False
            
            self.seen_ids.add(record_id)
            
            # Parse content if it's JSON, otherwise wrap it
            try:
                content_obj = json.loads(content)
            except:
                content_obj = {"raw": content}
            
            record = {"id": record_id, **content_obj}
            self.file.write(json.dumps(record) + "\n")
            self.stats["inserted"] += 1
            return True
            
        except Exception as e:
            self.stats["errors"] += 1
            logger.error(f"Error writing ID {record_id}: {e}")
            return False
    
    def commit(self):
        self.file.flush()
    
    def close(self):
        self.commit()
        self.file.close()
        logger.info(f"JSONLSink closed. Final stats: {self.stats}")
    
    def get_stats(self) -> Dict[str, int]:
        return self.stats.copy()
