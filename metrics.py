"""
Prometheus metrics for ES-MySQL pipeline monitoring

Provides comprehensive observability for:
- Throughput (records processed, inserted, skipped, failed)
- Latency (fetch, insert, batch, end-to-end)
- Resource utilization (workers, queue depth)
- Error tracking (by type and severity)

Author: Mac McAllorum (kevin_mcallorum@linux.com)
GitHub: github.com/kmcallorum
License: MIT
"""
from prometheus_client import Counter, Gauge, Histogram, Summary, Info
import time
from contextlib import contextmanager
from typing import Optional, Dict, Any
import logging

logger = logging.getLogger(__name__)


# =============================================================================
# COUNTERS - Things that only go up
# =============================================================================

# Total records processed by the pipeline
records_processed_total = Counter(
    'pipeline_records_processed_total',
    'Total number of records processed',
    ['source_type', 'sink_type']
)

# Records successfully inserted
records_inserted_total = Counter(
    'pipeline_records_inserted_total',
    'Total number of records successfully inserted',
    ['source_type', 'sink_type']
)

# Records skipped (duplicates, etc.)
records_skipped_total = Counter(
    'pipeline_records_skipped_total',
    'Total number of records skipped',
    ['source_type', 'sink_type', 'reason']
)

# Records that failed
records_failed_total = Counter(
    'pipeline_records_failed_total',
    'Total number of records that failed',
    ['source_type', 'sink_type', 'error_type']
)

# Pipeline runs (successful and failed)
pipeline_runs_total = Counter(
    'pipeline_runs_total',
    'Total number of pipeline runs',
    ['source_type', 'sink_type', 'status']
)

# AI error analysis requests
ai_analysis_requests_total = Counter(
    'pipeline_ai_analysis_requests_total',
    'Total number of AI error analysis requests',
    ['analyzer_type', 'status']
)


# =============================================================================
# GAUGES - Things that go up and down
# =============================================================================

# Current active workers
active_workers = Gauge(
    'pipeline_active_workers',
    'Number of currently active worker threads',
    ['pipeline_id']
)

# Current queue depth
queue_depth = Gauge(
    'pipeline_queue_depth',
    'Current number of items in processing queue',
    ['pipeline_id']
)

# Pipeline state (0=stopped, 1=running, 2=error)
pipeline_state = Gauge(
    'pipeline_state',
    'Current pipeline state (0=stopped, 1=running, 2=error)',
    ['pipeline_id']
)


# =============================================================================
# HISTOGRAMS - Distribution of values
# =============================================================================

# Fetch operation latency
fetch_duration_seconds = Histogram(
    'pipeline_fetch_duration_seconds',
    'Time spent fetching records from source',
    ['source_type'],
    buckets=(0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0)
)

# Insert operation latency
insert_duration_seconds = Histogram(
    'pipeline_insert_duration_seconds',
    'Time spent inserting a single record',
    ['sink_type'],
    buckets=(0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5)
)

# Batch processing latency
batch_duration_seconds = Histogram(
    'pipeline_batch_duration_seconds',
    'Time spent processing a batch of records',
    ['source_type', 'sink_type'],
    buckets=(0.1, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0, 120.0)
)

# Batch size distribution
batch_size = Histogram(
    'pipeline_batch_size',
    'Number of records in each batch',
    ['source_type'],
    buckets=(10, 50, 100, 250, 500, 1000, 2500, 5000, 10000)
)


# =============================================================================
# SUMMARY - Percentiles and totals
# =============================================================================

# End-to-end pipeline run duration
pipeline_run_duration_seconds = Summary(
    'pipeline_run_duration_seconds',
    'Total duration of pipeline run',
    ['source_type', 'sink_type', 'status']
)


# =============================================================================
# INFO - Metadata
# =============================================================================

# Pipeline build/version info
pipeline_info = Info(
    'pipeline_info',
    'Pipeline version and configuration information'
)


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

@contextmanager
def time_operation(metric: Histogram, **labels):
    """
    Context manager to time an operation and record it in a histogram.
    
    Usage:
        with time_operation(fetch_duration_seconds, source_type="elasticsearch"):
            # ... do fetch operation
            pass
    """
    start_time = time.time()
    try:
        yield
    finally:
        duration = time.time() - start_time
        metric.labels(**labels).observe(duration)


def record_success(source_type: str, sink_type: str):
    """Record a successful record insertion"""
    records_processed_total.labels(source_type=source_type, sink_type=sink_type).inc()
    records_inserted_total.labels(source_type=source_type, sink_type=sink_type).inc()


def record_skip(source_type: str, sink_type: str, reason: str = "duplicate"):
    """Record a skipped record"""
    records_processed_total.labels(source_type=source_type, sink_type=sink_type).inc()
    records_skipped_total.labels(source_type=source_type, sink_type=sink_type, reason=reason).inc()


def record_failure(source_type: str, sink_type: str, error: Exception):
    """Record a failed record"""
    error_type = type(error).__name__
    records_processed_total.labels(source_type=source_type, sink_type=sink_type).inc()
    records_failed_total.labels(source_type=source_type, sink_type=sink_type, error_type=error_type).inc()


def record_ai_analysis(analyzer_type: str, success: bool):
    """Record an AI analysis request"""
    status = "success" if success else "failure"
    ai_analysis_requests_total.labels(analyzer_type=analyzer_type, status=status).inc()


def set_pipeline_info(version: str = "1.0.0", **kwargs):
    """Set pipeline metadata"""
    info = {"version": version}
    info.update(kwargs)
    pipeline_info.info(info)


def get_metrics_summary() -> Dict[str, Any]:
    """
    Get a summary of current metrics for logging/debugging.
    
    Returns:
        Dictionary with current metric values
    """
    # Note: This is a simple summary, not all metric values
    return {
        "metrics_registered": True,
        "counters": [
            "records_processed_total",
            "records_inserted_total",
            "records_skipped_total",
            "records_failed_total",
            "pipeline_runs_total",
            "ai_analysis_requests_total"
        ],
        "gauges": [
            "active_workers",
            "queue_depth",
            "pipeline_state"
        ],
        "histograms": [
            "fetch_duration_seconds",
            "insert_duration_seconds",
            "batch_duration_seconds",
            "batch_size"
        ]
    }


# Initialize pipeline info on module load
set_pipeline_info(
    version="1.0.0",
    author="Mac McAllorum",
    project="es-to-mysql-pipeline"
)

logger.info("Prometheus metrics initialized")
