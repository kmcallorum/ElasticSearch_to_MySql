"""
Data pipeline with dependency injection and Prometheus metrics

Processes records from source to sink with optional metrics collection.

Author: Mac McAllorum (kevin_mcallorum@linux.com)
GitHub: github.com/kmcallorum
License: MIT
"""
import logging
import threading
import time
from queue import Queue
from typing import Optional, Dict, Any
from data_interfaces import DataSource, DataSink
from error_analyzer import ErrorAnalyzer, NoOpErrorAnalyzer

logger = logging.getLogger(__name__)

# Optional Prometheus metrics support
try:
    import metrics
    METRICS_AVAILABLE = True
    logger.debug("Prometheus metrics enabled")
except ImportError:
    METRICS_AVAILABLE = False
    logger.debug("Prometheus metrics not available (prometheus_client not installed)")


class DataPipeline:
    """
    Main pipeline that orchestrates data movement from source to sink.
    Uses dependency injection for testability and optional Prometheus metrics.
    """
    
    def __init__(self, source: DataSource, sink: DataSink, num_threads: int = 5,
                 error_analyzer: Optional[ErrorAnalyzer] = None,
                 enable_metrics: bool = True,
                 pipeline_id: str = "default"):
        """
        Args:
            source: DataSource implementation
            sink: DataSink implementation  
            num_threads: Number of worker threads for parallel processing
            error_analyzer: Optional ErrorAnalyzer for AI-powered troubleshooting
            enable_metrics: Enable Prometheus metrics collection (default: True)
            pipeline_id: Unique identifier for this pipeline instance (for metrics)
        """
        self.source = source
        self.sink = sink
        self.num_threads = num_threads
        self.error_analyzer = error_analyzer or NoOpErrorAnalyzer()
        self.total_processed = 0
        self.enable_metrics = enable_metrics and METRICS_AVAILABLE
        self.pipeline_id = pipeline_id
        
        # Determine source and sink types for metrics labels
        self.source_type = type(source).__name__.replace('Source', '').lower()
        self.sink_type = type(sink).__name__.replace('Sink', '').lower()
        
        if self.enable_metrics:
            logger.debug(f"Metrics enabled for pipeline: {self.pipeline_id}")
            # Set pipeline state to stopped initially
            metrics.pipeline_state.labels(pipeline_id=self.pipeline_id).set(0)
    
    def run(self, query_params: Optional[Dict[str, Any]] = None):
        """
        Execute the pipeline: fetch from source and insert into sink.
        
        Args:
            query_params: Optional parameters to pass to the data source
        
        Returns:
            Statistics dictionary with counts
        """
        logger.info(f"Starting pipeline with {self.num_threads} threads")
        
        start_time = time.time()
        status = "success"
        
        try:
            # Set pipeline state to running
            if self.enable_metrics:
                metrics.pipeline_state.labels(pipeline_id=self.pipeline_id).set(1)
            
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
            
            # Record metrics
            if self.enable_metrics:
                # Update counters based on final stats
                if stats.get("inserted", 0) > 0:
                    metrics.records_inserted_total.labels(
                        source_type=self.source_type,
                        sink_type=self.sink_type
                    ).inc(stats["inserted"])
                
                if stats.get("skipped", 0) > 0:
                    metrics.records_skipped_total.labels(
                        source_type=self.source_type,
                        sink_type=self.sink_type,
                        reason="duplicate"
                    ).inc(stats["skipped"])
                
                if stats.get("errors", 0) > 0:
                    metrics.records_failed_total.labels(
                        source_type=self.source_type,
                        sink_type=self.sink_type,
                        error_type="various"
                    ).inc(stats["errors"])
            
            return stats
            
        except Exception as e:
            status = "failure"
            logger.error(f"Pipeline failed: {e}")
            raise
            
        finally:
            # Record run duration and increment run counter
            duration = time.time() - start_time
            
            if self.enable_metrics:
                metrics.pipeline_run_duration_seconds.labels(
                    source_type=self.source_type,
                    sink_type=self.sink_type,
                    status=status
                ).observe(duration)
                
                metrics.pipeline_runs_total.labels(
                    source_type=self.source_type,
                    sink_type=self.sink_type,
                    status=status
                ).inc()
                
                # Set pipeline state back to stopped (or error)
                state_value = 0 if status == "success" else 2
                metrics.pipeline_state.labels(pipeline_id=self.pipeline_id).set(state_value)
    
    def _run_single_threaded(self, query_params: Optional[Dict[str, Any]]):
        """Single-threaded execution (safer for file-based sinks)"""
        try:
            for record_id, content in self.source.fetch_records(query_params):
                try:
                    # Time the insert operation
                    if self.enable_metrics:
                        with metrics.time_operation(
                            metrics.insert_duration_seconds,
                            sink_type=self.sink_type
                        ):
                            result = self.sink.insert_record(record_id, content)
                    else:
                        result = self.sink.insert_record(record_id, content)
                    
                    self.total_processed += 1
                    
                    # Track individual record metrics
                    if self.enable_metrics:
                        metrics.records_processed_total.labels(
                            source_type=self.source_type,
                            sink_type=self.sink_type
                        ).inc()
                    
                    if self.total_processed % 100 == 0:
                        logger.info(f"Processed {self.total_processed} records")
                        
                except Exception as e:
                    self._handle_error(e, {
                        "operation": "sink_insert",
                        "record_id": record_id,
                        "total_processed": self.total_processed
                    })
                    # Continue processing other records
                    
        except Exception as e:
            self._handle_error(e, {
                "operation": "source_fetch",
                "total_processed": self.total_processed
            })
            raise  # Re-raise source errors as they're fatal
    
    def _run_multi_threaded(self, query_params: Optional[Dict[str, Any]]):
        """Multi-threaded execution (for thread-safe sinks like MySQL)"""
        queue = Queue()
        threads = []
        
        # Update active workers gauge
        if self.enable_metrics:
            metrics.active_workers.labels(pipeline_id=self.pipeline_id).set(self.num_threads)
        
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
        batch_start = time.time()
        batch_count = 0
        
        for record_id, content in self.source.fetch_records(query_params):
            queue.put((record_id, content))
            self.total_processed += 1
            batch_count += 1
            
            # Update queue depth gauge
            if self.enable_metrics:
                metrics.queue_depth.labels(pipeline_id=self.pipeline_id).set(queue.qsize())
            
            if self.total_processed % 100 == 0:
                logger.info(f"Queued {self.total_processed} records")
                
                # Record batch metrics
                if self.enable_metrics:
                    batch_duration = time.time() - batch_start
                    metrics.batch_duration_seconds.labels(
                        source_type=self.source_type,
                        sink_type=self.sink_type
                    ).observe(batch_duration)
                    metrics.batch_size.labels(source_type=self.source_type).observe(batch_count)
                    
                    batch_start = time.time()
                    batch_count = 0
        
        # Wait for queue to empty and stop workers
        queue.join()
        for _ in threads:
            queue.put(None)  # Poison pill
        for t in threads:
            t.join()
        
        # Reset gauges
        if self.enable_metrics:
            metrics.active_workers.labels(pipeline_id=self.pipeline_id).set(0)
            metrics.queue_depth.labels(pipeline_id=self.pipeline_id).set(0)
    
    def _insert_worker(self, queue: Queue):
        """Worker thread that processes items from queue"""
        worker_stats = {"processed": 0, "inserted": 0, "skipped": 0}
        
        while True:
            item = queue.get()
            if item is None:  # Poison pill
                break
            
            record_id, content = item
            
            # Time the insert operation
            if self.enable_metrics:
                with metrics.time_operation(
                    metrics.insert_duration_seconds,
                    sink_type=self.sink_type
                ):
                    inserted = self.sink.insert_record(record_id, content)
            else:
                inserted = self.sink.insert_record(record_id, content)
            
            worker_stats["processed"] += 1
            if inserted:
                worker_stats["inserted"] += 1
            else:
                worker_stats["skipped"] += 1
            
            # Track individual record metrics
            if self.enable_metrics:
                metrics.records_processed_total.labels(
                    source_type=self.source_type,
                    sink_type=self.sink_type
                ).inc()
            
            if worker_stats["processed"] % 100 == 0:
                logger.debug(f"{threading.current_thread().name} - {worker_stats}")
            
            queue.task_done()
        
        logger.info(f"{threading.current_thread().name} finished: {worker_stats}")
    
    def cleanup(self):
        """Clean up resources"""
        self.source.close()
        self.sink.close()
    
    def _handle_error(self, error: Exception, context: Dict[str, Any]):
        """
        Handle an error with optional AI analysis
        
        Args:
            error: The exception that occurred
            context: Context about where/when the error occurred
        """
        # Log the error
        logger.error(f"Error in {context.get('operation', 'unknown')}: {error}")
        
        # Track error metrics
        if self.enable_metrics:
            error_type = type(error).__name__
            metrics.records_failed_total.labels(
                source_type=self.source_type,
                sink_type=self.sink_type,
                error_type=error_type
            ).inc()
        
        # Get AI suggestions if analyzer is enabled
        if self.error_analyzer.is_enabled():
            try:
                suggestions = self.error_analyzer.analyze_error(error, context)
                
                # Track AI analysis metrics
                if self.enable_metrics:
                    analyzer_type = type(self.error_analyzer).__name__
                    success = suggestions is not None
                    metrics.record_ai_analysis(analyzer_type, success)
                
                if suggestions:
                    logger.info(f"\n{suggestions}\n")
                    
            except Exception as analysis_error:
                logger.debug(f"Error analysis failed (non-critical): {analysis_error}")
                
                # Track failed AI analysis
                if self.enable_metrics:
                    analyzer_type = type(self.error_analyzer).__name__
                    metrics.record_ai_analysis(analyzer_type, False)
