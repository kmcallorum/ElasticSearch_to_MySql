"""
Data pipeline with dependency injection - processes records from source to sink

Author: Kevin McAllorum (kevin_mcallorum@linux.com)
GitHub: github.com/kmcallorum
License: MIT
"""
import logging
import threading
from queue import Queue
from typing import Optional, Dict, Any
from data_interfaces import DataSource, DataSink

logger = logging.getLogger(__name__)


class DataPipeline:
    """
    Main pipeline that orchestrates data movement from source to sink.
    Uses dependency injection for testability.
    """
    
    def __init__(self, source: DataSource, sink: DataSink, num_threads: int = 5):
        """
        Args:
            source: DataSource implementation
            sink: DataSink implementation  
            num_threads: Number of worker threads for parallel processing
        """
        self.source = source
        self.sink = sink
        self.num_threads = num_threads
        self.total_processed = 0
    
    def run(self, query_params: Optional[Dict[str, Any]] = None):
        """
        Execute the pipeline: fetch from source and insert into sink.
        
        Args:
            query_params: Optional parameters to pass to the data source
        """
        logger.info(f"Starting pipeline with {self.num_threads} threads")
        
        # Single-threaded for sinks that aren't thread-safe (like file writes)
        if self.num_threads == 1:
            self._run_single_threaded(query_params)
        else:
            self._run_multi_threaded(query_params)
        
        # Final commit and stats
        self.sink.commit()
        stats = self.sink.get_stats()
        logger.info(f"Pipeline completed. Total processed: {self.total_processed}")
        logger.info(f"Final stats: {stats}")
        
        return stats
    
    def _run_single_threaded(self, query_params: Optional[Dict[str, Any]]):
        """Single-threaded execution (safer for file-based sinks)"""
        for record_id, content in self.source.fetch_records(query_params):
            self.sink.insert_record(record_id, content)
            self.total_processed += 1
            
            if self.total_processed % 100 == 0:
                logger.info(f"Processed {self.total_processed} records")
    
    def _run_multi_threaded(self, query_params: Optional[Dict[str, Any]]):
        """Multi-threaded execution (for thread-safe sinks like MySQL)"""
        queue = Queue()
        threads = []
        
        # Start worker threads
        for i in range(self.num_threads):
            t = threading.Thread(
                target=self._insert_worker,
                args=(queue,),
                name=f"Worker-{i+1}"
            )
            t.start()
            threads.append(t)
        
        # Feed queue from source
        for record_id, content in self.source.fetch_records(query_params):
            queue.put((record_id, content))
            self.total_processed += 1
            
            if self.total_processed % 100 == 0:
                logger.info(f"Queued {self.total_processed} records")
        
        # Wait for queue to empty and stop workers
        queue.join()
        for _ in threads:
            queue.put(None)  # Poison pill
        for t in threads:
            t.join()
    
    def _insert_worker(self, queue: Queue):
        """Worker thread that processes items from queue"""
        worker_stats = {"processed": 0, "inserted": 0, "skipped": 0}
        
        while True:
            item = queue.get()
            if item is None:  # Poison pill
                break
            
            record_id, content = item
            inserted = self.sink.insert_record(record_id, content)
            
            worker_stats["processed"] += 1
            if inserted:
                worker_stats["inserted"] += 1
            else:
                worker_stats["skipped"] += 1
            
            if worker_stats["processed"] % 100 == 0:
                logger.debug(f"{threading.current_thread().name} - {worker_stats}")
            
            queue.task_done()
        
        logger.info(f"{threading.current_thread().name} finished: {worker_stats}")
    
    def cleanup(self):
        """Clean up resources"""
        self.source.close()
        self.sink.close()
