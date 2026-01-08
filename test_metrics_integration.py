"""
Tests for metrics integration in pipeline and CLI

Covers the instrumented code paths to achieve 100% coverage.

Author: Kevin McAllorum
"""
import pytest
import tempfile
import csv
import os
import time
from unittest.mock import Mock, patch


class TestPipelineWithMetrics:
    """Test DataPipeline with metrics enabled"""
    
    def test_pipeline_with_metrics_enabled(self):
        """Test pipeline runs with metrics enabled"""
        from test_impl import CSVSource, FileSink
        from pipeline import DataPipeline
        
        # Create test CSV
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            writer = csv.DictWriter(f, fieldnames=["id", "data"])
            writer.writeheader()
            writer.writerow({"id": "1", "data": "test"})
            csv_path = f.name
        
        output_path = tempfile.NamedTemporaryFile(suffix='.txt', delete=False).name
        
        try:
            source = CSVSource(csv_path)
            sink = FileSink(output_path)
            
            # Create pipeline with metrics enabled
            pipeline = DataPipeline(
                source, 
                sink, 
                num_threads=1,
                enable_metrics=True,
                pipeline_id="test-metrics"
            )
            
            stats = pipeline.run()
            pipeline.cleanup()
            
            assert stats["inserted"] >= 1
            
        finally:
            if os.path.exists(csv_path):
                os.unlink(csv_path)
            if os.path.exists(output_path):
                os.unlink(output_path)
    
    def test_pipeline_with_metrics_disabled(self):
        """Test pipeline runs with metrics explicitly disabled"""
        from test_impl import CSVSource, FileSink
        from pipeline import DataPipeline
        
        # Create test CSV
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            writer = csv.DictWriter(f, fieldnames=["id", "data"])
            writer.writeheader()
            writer.writerow({"id": "1", "data": "test"})
            csv_path = f.name
        
        output_path = tempfile.NamedTemporaryFile(suffix='.txt', delete=False).name
        
        try:
            source = CSVSource(csv_path)
            sink = FileSink(output_path)
            
            # Create pipeline with metrics disabled
            pipeline = DataPipeline(
                source, 
                sink, 
                num_threads=1,
                enable_metrics=False,
                pipeline_id="test-no-metrics"
            )
            
            stats = pipeline.run()
            pipeline.cleanup()
            
            assert stats["inserted"] >= 1
            
        finally:
            if os.path.exists(csv_path):
                os.unlink(csv_path)
            if os.path.exists(output_path):
                os.unlink(output_path)
    
    def test_pipeline_multithreaded_with_metrics(self):
        """Test multi-threaded pipeline with metrics"""
        from test_impl import CSVSource, JSONLSink
        from pipeline import DataPipeline
        
        # Create test CSV
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            writer = csv.DictWriter(f, fieldnames=["id", "data"])
            writer.writeheader()
            for i in range(10):
                writer.writerow({"id": str(i), "data": f"test{i}"})
            csv_path = f.name
        
        output_path = tempfile.NamedTemporaryFile(suffix='.jsonl', delete=False).name
        
        try:
            source = CSVSource(csv_path)
            sink = JSONLSink(output_path)
            
            # Multi-threaded with metrics
            pipeline = DataPipeline(
                source, 
                sink, 
                num_threads=2,
                enable_metrics=True,
                pipeline_id="test-mt-metrics"
            )
            
            stats = pipeline.run()
            pipeline.cleanup()
            
            assert stats["inserted"] == 10
            
        finally:
            if os.path.exists(csv_path):
                os.unlink(csv_path)
            if os.path.exists(output_path):
                os.unlink(output_path)
    
    def test_pipeline_error_with_metrics(self):
        """Test pipeline error handling with metrics enabled"""
        from test_impl import CSVSource
        from pipeline import DataPipeline
        from data_interfaces import DataSink
        
        # Create a sink that fails
        class FailingSink(DataSink):
            def __init__(self):
                self.stats = {"inserted": 0, "skipped": 0, "errors": 0}
            
            def insert_record(self, record_id, content):
                raise ValueError("Simulated insert error")
            
            def commit(self):
                pass
            
            def close(self):
                pass
            
            def get_stats(self):
                return self.stats
        
        # Create test CSV
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            writer = csv.DictWriter(f, fieldnames=["id", "data"])
            writer.writeheader()
            writer.writerow({"id": "1", "data": "test"})
            csv_path = f.name
        
        try:
            source = CSVSource(csv_path)
            sink = FailingSink()
            
            # Pipeline with failing sink and metrics enabled
            pipeline = DataPipeline(
                source, 
                sink, 
                num_threads=1,
                enable_metrics=True,
                pipeline_id="test-error-metrics"
            )
            
            # Should not raise exception (errors are logged)
            stats = pipeline.run()
            pipeline.cleanup()
            
        finally:
            if os.path.exists(csv_path):
                os.unlink(csv_path)


class TestCLIWithMetrics:
    """Test CLI with metrics flags"""
    
    @patch('pipeline_cli.MetricsServer')
    @patch('pipeline_cli.DataPipeline')
    @patch('pipeline_cli.CSVSource')
    @patch('pipeline_cli.FileSink')
    def test_cli_with_metrics_port(self, mock_sink, mock_source, mock_pipeline, mock_server):
        """Test CLI with --metrics-port flag"""
        from pipeline_cli import main
        
        # Setup mocks
        mock_source_instance = Mock()
        mock_source.return_value = mock_source_instance
        
        mock_sink_instance = Mock()
        mock_sink_instance.get_stats.return_value = {"inserted": 10, "skipped": 0, "errors": 0}
        mock_sink.return_value = mock_sink_instance
        
        mock_pipeline_instance = Mock()
        mock_pipeline_instance.run.return_value = {"inserted": 10, "skipped": 0, "errors": 0}
        mock_pipeline.return_value = mock_pipeline_instance
        
        mock_server_instance = Mock()
        mock_server_instance.is_running.return_value = False
        mock_server.return_value = mock_server_instance
        
        # Mock sys.argv
        test_args = [
            'pipeline_cli.py',
            '--source_type', 'csv',
            '--csv_file', 'test.csv',
            '--sink_type', 'file',
            '--output_file', 'output.txt',
            '--metrics-port', '8000'
        ]
        
        with patch('sys.argv', test_args):
            with patch('signal.signal'):
                try:
                    main()
                except SystemExit:  # pragma: no cover
                    pass  # pragma: no cover
        
        # Verify metrics server was started
        mock_server_instance.start.assert_called_once()
    
    @patch('pipeline_cli.DataPipeline')
    @patch('pipeline_cli.CSVSource')
    @patch('pipeline_cli.FileSink')
    def test_cli_without_metrics_port(self, mock_sink, mock_source, mock_pipeline):
        """Test CLI without --metrics-port flag"""
        from pipeline_cli import main
        
        # Setup mocks
        mock_source_instance = Mock()
        mock_source.return_value = mock_source_instance
        
        mock_sink_instance = Mock()
        mock_sink_instance.get_stats.return_value = {"inserted": 10, "skipped": 0, "errors": 0}
        mock_sink.return_value = mock_sink_instance
        
        mock_pipeline_instance = Mock()
        mock_pipeline_instance.run.return_value = {"inserted": 10, "skipped": 0, "errors": 0}
        mock_pipeline.return_value = mock_pipeline_instance
        
        # Mock sys.argv (no metrics-port)
        test_args = [
            'pipeline_cli.py',
            '--source_type', 'csv',
            '--csv_file', 'test.csv',
            '--sink_type', 'file',
            '--output_file', 'output.txt'
        ]
        
        with patch('sys.argv', test_args):
            try:
                main()
            except SystemExit:  # pragma: no cover
                pass  # pragma: no cover
        
        # Pipeline should be created without metrics
        assert mock_pipeline.called
    
    def test_cli_metrics_not_available(self):
        """Test CLI when prometheus_client not installed"""
        from pipeline_cli import main
        
        # Mock sys.argv with metrics-port
        test_args = [
            'pipeline_cli.py',
            '--source_type', 'csv',
            '--csv_file', 'test.csv',
            '--sink_type', 'file',
            '--output_file', 'output.txt',
            '--metrics-port', '8000'
        ]
        
        with patch('sys.argv', test_args):
            with patch('pipeline_cli.METRICS_AVAILABLE', False):
                with pytest.raises(SystemExit) as exc_info:
                    main()
                
                assert exc_info.value.code == 1
    
    @patch('pipeline_cli.MetricsServer')
    @patch('pipeline_cli.DataPipeline')
    @patch('pipeline_cli.CSVSource')
    @patch('pipeline_cli.FileSink')
    def test_cli_with_custom_pipeline_id(self, mock_sink, mock_source, mock_pipeline, mock_server):
        """Test CLI with custom pipeline-id"""
        from pipeline_cli import main
        
        # Setup mocks
        mock_source_instance = Mock()
        mock_source.return_value = mock_source_instance
        
        mock_sink_instance = Mock()
        mock_sink_instance.get_stats.return_value = {"inserted": 10, "skipped": 0, "errors": 0}
        mock_sink.return_value = mock_sink_instance
        
        mock_pipeline_instance = Mock()
        mock_pipeline_instance.run.return_value = {"inserted": 10, "skipped": 0, "errors": 0}
        mock_pipeline.return_value = mock_pipeline_instance
        
        mock_server_instance = Mock()
        mock_server_instance.is_running.return_value = False
        mock_server.return_value = mock_server_instance
        
        # Mock sys.argv with pipeline-id
        test_args = [
            'pipeline_cli.py',
            '--source_type', 'csv',
            '--csv_file', 'test.csv',
            '--sink_type', 'file',
            '--output_file', 'output.txt',
            '--metrics-port', '8000',
            '--pipeline-id', 'my-custom-pipeline'
        ]
        
        with patch('sys.argv', test_args):
            with patch('signal.signal'):
                try:
                    main()
                except SystemExit:  # pragma: no cover
                    pass  # pragma: no cover
        
        # Verify pipeline created with custom ID
        call_args = mock_pipeline.call_args
        assert call_args[1]['pipeline_id'] == 'my-custom-pipeline'


class TestMetricsServerEdgeCases:
    """Additional metrics server tests for coverage"""
    
    def test_metrics_server_stop_when_not_running(self):
        """Test stopping server that was never started"""
        from metrics_server import MetricsServer
        
        server = MetricsServer(port=9500)
        # Should not raise exception
        server.stop()
        assert not server.is_running()
    
    def test_metrics_handler_logging(self):
        """Test MetricsHandler log_message method"""
        from metrics_server import MetricsServer
        
        # Create a mock server
        with MetricsServer(port=9501) as server:
            time.sleep(0.1)
            # Server is running, log_message is used internally
            assert server.is_running()


if __name__ == "__main__":  # pragma: no cover
    pytest.main([__file__, "-v"])
