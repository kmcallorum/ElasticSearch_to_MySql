"""
CLI entry point with dependency injection and Prometheus metrics support

Author: Kevin McAllorum (kevin_mcallorum@linux.com)
GitHub: github.com/kmcallorum
License: MIT
"""
import argparse
import logging
import sys
import signal
from pipeline import DataPipeline
from production_impl import ElasticsearchSource, MySQLSink
from test_impl import CSVSource, FileSink, JSONLSink
from error_analyzer import ClaudeErrorAnalyzer, SimpleErrorAnalyzer, NoOpErrorAnalyzer
from jsonl_source import JSONLSource

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("pipeline.log"),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Optional metrics support
try:
    from metrics_server import MetricsServer
    METRICS_AVAILABLE = True
except ImportError:
    METRICS_AVAILABLE = False
    logger.debug("Metrics server not available (prometheus_client not installed)")


def create_source(args):
    """Factory function to create appropriate data source"""
    if args.source_type == "elasticsearch":
        return ElasticsearchSource(
            es_url=args.es_url,
            batch_size=args.batch_size,
            es_user=args.es_user,
            es_pass=args.es_pass,
            api_key=args.api_key
        )
    elif args.source_type == "csv":
        return CSVSource(
            filepath=args.csv_file,
            id_column=args.csv_id_column,
            content_column=args.csv_content_column
        )
    elif args.source_type == "jsonl":
        return JSONLSource(
            filepath=args.jsonl_file,
            id_field=args.jsonl_id_field,
            content_field=args.jsonl_content_field
    )
    else:
        raise ValueError(f"Unknown source type: {args.source_type}")


def create_sink(args):
    """Factory function to create appropriate data sink"""
    if args.sink_type == "mysql":
        return MySQLSink(
            host=args.db_host,
            user=args.db_user,
            password=args.db_pass,
            database=args.db_name,
            table=args.db_table
        )
    elif args.sink_type == "file":
        return FileSink(filepath=args.output_file)
    elif args.sink_type == "jsonl":
        return JSONLSink(filepath=args.output_file)
    else:
        raise ValueError(f"Unknown sink type: {args.sink_type}")


def create_error_analyzer(args):
    """Factory function to create error analyzer"""
    if args.ai_errors:
        return ClaudeErrorAnalyzer()
    elif args.simple_errors:
        return SimpleErrorAnalyzer()
    else:
        return NoOpErrorAnalyzer()


def build_query_params(args):
    """Build query parameters dict from args"""
    params = {}
    
    if hasattr(args, 'match_all') and args.match_all:
        params["match_all"] = True
    
    if hasattr(args, 'gte') and args.gte:
        params["gte"] = args.gte
    
    if hasattr(args, 'lte') and args.lte:
        params["lte"] = args.lte
    
    if hasattr(args, 'limit') and args.limit:
        params["limit"] = args.limit
    
    return params if params else None


def main():
    parser = argparse.ArgumentParser(
        description="Data pipeline with pluggable source and sink implementations + Prometheus metrics"
    )
    
    # Source/Sink selection
    parser.add_argument("--source_type", required=True, 
                       choices=["elasticsearch", "csv", "jsonl"],
                       help="Type of data source")
    parser.add_argument("--sink_type", required=True,
                       choices=["mysql", "file", "jsonl"],
                       help="Type of data sink")
    
    # Elasticsearch source args
    parser.add_argument("--es_url", help="Elasticsearch URL")
    parser.add_argument("--es_user", help="Elasticsearch username")
    parser.add_argument("--es_pass", help="Elasticsearch password")
    parser.add_argument("--api_key", help="Elasticsearch API Key")
    parser.add_argument("--batch_size", type=int, default=1000)
    
    # CSV source args
    parser.add_argument("--csv_file", help="Path to CSV file")
    parser.add_argument("--csv_id_column", default="id", help="CSV column name for record ID")
    parser.add_argument("--csv_content_column", default="content", help="CSV column name for content")
    
    # MySQL sink args
    parser.add_argument("--db_host", help="MySQL host")
    parser.add_argument("--db_user", help="MySQL user")
    parser.add_argument("--db_pass", help="MySQL password")
    parser.add_argument("--db_name", help="MySQL database")
    parser.add_argument("--db_table", help="MySQL table")
    
    # File sink args
    parser.add_argument("--output_file", help="Output file path for file/jsonl sink")
    
    # Query options
    parser.add_argument("--gte", help="Start date for ES query")
    parser.add_argument("--lte", help="End date for ES query")
    parser.add_argument("--match_all", action="store_true", help="Use match_all query for ES")
    parser.add_argument("--limit", type=int, help="Limit number of records (for testing)")
    
    # Pipeline options
    parser.add_argument("--threads", type=int, default=1, 
                       help="Number of threads (use 1 for file sinks, 5+ for MySQL)")
    parser.add_argument("--pipeline-id", default="default",
                       help="Unique identifier for this pipeline instance (for metrics)")
    
    # Error analysis options
    parser.add_argument("--ai-errors", action="store_true",
                       help="Enable AI-powered error analysis (requires ANTHROPIC_API_KEY env var)")
    parser.add_argument("--simple-errors", action="store_true",
                       help="Enable simple rule-based error suggestions (no API required)")
    
    # Metrics options
    parser.add_argument("--metrics-port", type=int,
                       help="Enable Prometheus metrics server on specified port (e.g., 8000)")
    parser.add_argument("--metrics-host", default="0.0.0.0",
                       help="Host for metrics server (default: 0.0.0.0)")
    
    parser.add_argument('--jsonl_file', help='Path to JSONL file')
    parser.add_argument('--jsonl_id_field', default='id')
    parser.add_argument('--jsonl_content_field', default='content')
    
    args = parser.parse_args()
    
    # Check if metrics are requested but not available
    if args.metrics_port and not METRICS_AVAILABLE:
        logger.error("Metrics requested but prometheus_client not installed!")
        logger.error("Install with: pip install prometheus_client")
        sys.exit(1)
    
    metrics_server = None
    
    try:
        # Start metrics server if requested
        if args.metrics_port:
            logger.info(f"Starting metrics server on {args.metrics_host}:{args.metrics_port}")
            metrics_server = MetricsServer(port=args.metrics_port, host=args.metrics_host)
            metrics_server.start()
            logger.info(f"Metrics available at: http://{args.metrics_host}:{args.metrics_port}/metrics")
        
        # Create source and sink via dependency injection
        source = create_source(args)
        sink = create_sink(args)
        error_analyzer = create_error_analyzer(args)
        
        # Create and run pipeline
        pipeline = DataPipeline(
            source, 
            sink, 
            num_threads=args.threads,
            error_analyzer=error_analyzer,
            enable_metrics=args.metrics_port is not None,
            pipeline_id=args.pipeline_id
        )
        
        query_params = build_query_params(args)
        
        # Handle Ctrl+C gracefully
        def signal_handler(sig, frame):
            logger.info("\n\nShutting down gracefully...")
            pipeline.cleanup()
            if metrics_server:
                metrics_server.stop()
            sys.exit(0)
        
        signal.signal(signal.SIGINT, signal_handler)
        
        # Run pipeline
        stats = pipeline.run(query_params)
        
        # Cleanup
        pipeline.cleanup()
        
        # Print summary
        logger.info("=" * 60)
        logger.info("PIPELINE SUMMARY")
        logger.info(f"Source: {args.source_type}")
        logger.info(f"Sink: {args.sink_type}")
        logger.info(f"Records inserted: {stats['inserted']}")
        logger.info(f"Records skipped: {stats['skipped']}")
        logger.info(f"Errors: {stats['errors']}")
        if args.metrics_port:
            logger.info(f"Metrics: http://{args.metrics_host}:{args.metrics_port}/metrics")
        logger.info("=" * 60)
        # AI Error Analysis (NEW CODE)
        if stats['errors'] > 0 and error_analyzer and hasattr(error_analyzer, 'analyze_errors'):
            logger.info("")
            logger.info("=" * 60)
            logger.info("AI ERROR ANALYSIS")
            logger.info("=" * 60)

            try:
                analysis = error_analyzer.analyze_errors(
                    operation="pipeline_execution",
                    error_count=stats['errors'],
                    context={
                        "source_type": args.source_type,
                        "sink_type": args.sink_type,
                        "total_records": stats['inserted'] + stats['skipped'] + stats['errors'],
                        "success_rate": f"{(stats['inserted'] / (stats['inserted'] + stats['errors']) * 100):.1f}%" if (stats['inserted'] + stats['errors']) > 0 else "0%"
                    }
                )

                logger.info(f"\n{analysis}\n")
                logger.info("=" * 60)
            except Exception as e:
                logger.error(f"AI analysis failed: {e}")

        # Keep metrics server running if requested (for Prometheus to scrape)
        if metrics_server and metrics_server.is_running():
            logger.info("\nMetrics server still running for Prometheus scraping...")
            logger.info("Press Ctrl+C to stop")
            try:
                # Keep main thread alive
                signal.pause()
            except AttributeError:
                # signal.pause() not available on Windows
                import time
                while True:
                    time.sleep(1)
        
    except KeyboardInterrupt:
        logger.info("\n\nInterrupted by user")
        
    except Exception as e:
        logger.error(f"Pipeline failed: {e}", exc_info=True)
        sys.exit(1)
        
    finally:
        # Ensure metrics server is stopped
        if metrics_server:
            metrics_server.stop()


if __name__ == "__main__":
    main()
