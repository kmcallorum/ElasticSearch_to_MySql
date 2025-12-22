"""
Abstract interfaces for data source and data sink to enable dependency injection

Author: Kevin McAllorum (kevin_mcallorum@linux.com)
GitHub: github.com/kmcallorum
License: MIT
"""
from abc import ABC, abstractmethod
from typing import Iterator, Tuple, Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)


class DataSource(ABC):
    """Abstract base class for data sources"""
    
    @abstractmethod
    def fetch_records(self, query_params: Optional[Dict[str, Any]] = None) -> Iterator[Tuple[str, str]]:
        """
        Fetch records from the data source.
        
        Args:
            query_params: Optional query parameters (e.g., date range, filters)
            
        Yields:
            Tuple[str, str]: (record_id, json_content)
        """
        pass  # pragma: no cover  ← Coverage ignores this line
    
    @abstractmethod
    def close(self):
        """Clean up any resources"""
        pass  # pragma: no cover  ← Coverage ignores this line


class DataSink(ABC):
    """Abstract base class for data sinks"""
    
    @abstractmethod
    def insert_record(self, record_id: str, content: str) -> bool:
        """
        Insert a single record into the sink.
        
        Args:
            record_id: Unique identifier for the record
            content: JSON string content
            
        Returns:
            bool: True if inserted, False if skipped (duplicate)
        """
        pass  # pragma: no cover  ← Coverage ignores this line
    
    @abstractmethod
    def commit(self):
        """Commit any pending transactions"""
        pass  # pragma: no cover  ← Coverage ignores this line
    
    @abstractmethod
    def close(self):
        """Clean up any resources"""
        pass  # pragma: no cover  ← Coverage ignores this line
    
    @abstractmethod
    def get_stats(self) -> Dict[str, int]:
        """
        Get statistics about the operations.
        
        Returns:
            Dict with keys like 'inserted', 'skipped', 'errors'
        """
        pass  # pragma: no cover  ← Coverage ignores this line
