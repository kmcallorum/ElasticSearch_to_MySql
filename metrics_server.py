"""
Prometheus metrics HTTP server

Provides HTTP endpoints for Prometheus scraping:
- GET /metrics - Prometheus format metrics
- GET /health - Health check endpoint
- GET / - Basic info page

Author: Mac McAllorum (kevin_mcallorum@linux.com)
GitHub: github.com/kmcallorum
License: MIT
"""
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
from http.server import HTTPServer, BaseHTTPRequestHandler
import threading
import logging
import json
from typing import Optional

logger = logging.getLogger(__name__)


class MetricsHandler(BaseHTTPRequestHandler):
    """HTTP request handler for metrics endpoints"""
    
    def log_message(self, format, *args):
        """Override to use Python logging instead of stderr"""
        logger.debug(f"{self.address_string()} - {format % args}")
    
    def do_GET(self):
        """Handle GET requests"""
        if self.path == '/metrics':
            self._serve_metrics()
        elif self.path == '/health':
            self._serve_health()
        elif self.path == '/' or self.path == '/info':
            self._serve_info()
        else:
            self._serve_404()
    
    def _serve_metrics(self):
        """Serve Prometheus metrics"""
        try:
            metrics = generate_latest()
            self.send_response(200)
            self.send_header('Content-Type', CONTENT_TYPE_LATEST)
            self.end_headers()
            self.wfile.write(metrics)
        except Exception as e:
            logger.error(f"Error serving metrics: {e}")
            self._serve_error(500, str(e))
    
    def _serve_health(self):
        """Serve health check"""
        health = {
            "status": "healthy",
            "service": "es-mysql-pipeline-metrics",
            "version": "1.0.0"
        }
        self._serve_json(health)
    
    def _serve_info(self):
        """Serve info page"""
        info = {
            "service": "ES-MySQL Pipeline Metrics",
            "version": "1.0.0",
            "author": "Mac McAllorum",
            "endpoints": {
                "/metrics": "Prometheus metrics (for scraping)",
                "/health": "Health check endpoint",
                "/info": "This page"
            }
        }
        self._serve_json(info)
    
    def _serve_json(self, data: dict):
        """Serve JSON response"""
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(data, indent=2).encode('utf-8'))
    
    def _serve_404(self):
        """Serve 404 Not Found"""
        self.send_response(404)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        error = {"error": "Not Found", "path": self.path}
        self.wfile.write(json.dumps(error).encode('utf-8'))
    
    def _serve_error(self, code: int, message: str):
        """Serve error response"""
        self.send_response(code)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        error = {"error": message, "code": code}
        self.wfile.write(json.dumps(error).encode('utf-8'))


class MetricsServer:
    """
    HTTP server for Prometheus metrics.
    
    Runs in a background thread, non-blocking.
    """
    
    def __init__(self, port: int = 8000, host: str = '0.0.0.0'):
        """
        Initialize metrics server.
        
        Args:
            port: Port to listen on (default: 8000)
            host: Host to bind to (default: 0.0.0.0 for all interfaces)
        """
        self.port = port
        self.host = host
        self.server: Optional[HTTPServer] = None
        self.thread: Optional[threading.Thread] = None
        self._running = False
    
    def start(self):
        """Start the metrics server in a background thread"""
        if self._running:
            logger.warning("Metrics server already running")
            return
        
        try:
            self.server = HTTPServer((self.host, self.port), MetricsHandler)
            self._running = True
            
            # Start server in daemon thread so it doesn't block shutdown
            self.thread = threading.Thread(
                target=self._run_server,
                name="MetricsServer",
                daemon=True
            )
            self.thread.start()
            
            logger.info(f"Metrics server started on http://{self.host}:{self.port}")
            logger.info(f"  - Metrics: http://{self.host}:{self.port}/metrics")
            logger.info(f"  - Health:  http://{self.host}:{self.port}/health")
            
        except Exception as e:
            logger.error(f"Failed to start metrics server: {e}")
            self._running = False
            raise
    
    def _run_server(self):
        """Run the HTTP server (called in background thread)"""
        try:
            logger.debug("Metrics server thread started")
            self.server.serve_forever()
        except Exception as e:
            logger.error(f"Metrics server error: {e}")
        finally:
            logger.debug("Metrics server thread stopped")
    
    def stop(self):
        """Stop the metrics server"""
        if not self._running:
            return
        
        logger.info("Stopping metrics server...")
        self._running = False
        
        if self.server:
            self.server.shutdown()
            self.server.server_close()
        
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=5.0)
        
        logger.info("Metrics server stopped")
    
    def is_running(self) -> bool:
        """Check if server is running"""
        return self._running
    
    def get_url(self) -> str:
        """Get the base URL of the metrics server"""
        return f"http://{self.host}:{self.port}"
    
    def __enter__(self):
        """Context manager entry"""
        self.start()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.stop()


def start_metrics_server(port: int = 8000, host: str = '0.0.0.0') -> MetricsServer:
    """
    Convenience function to start a metrics server.
    
    Args:
        port: Port to listen on
        host: Host to bind to
    
    Returns:
        Running MetricsServer instance
    """
    server = MetricsServer(port=port, host=host)
    server.start()
    return server


if __name__ == "__main__":  # pragma: no cover
    # Simple test - start server and keep it running
    import time
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    print("Starting metrics server on http://localhost:8000")
    print("Press Ctrl+C to stop")
    print()
    print("Available endpoints:")
    print("  - http://localhost:8000/metrics  (Prometheus)")
    print("  - http://localhost:8000/health   (Health check)")
    print("  - http://localhost:8000/info     (Info)")
    
    server = start_metrics_server(port=8000)
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nShutting down...")
        server.stop()
