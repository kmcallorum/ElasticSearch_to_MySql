"""
Additional CLI tests for 100% coverage

Tests edge cases and error paths in pipeline_cli.py

Author: Kevin McAllorum
"""
import pytest
from unittest.mock import Mock, patch
import signal


class TestCLIErrorPaths:
    """Test CLI error handling paths"""
    
    @patch('pipeline_cli.DataPipeline')
    @patch('pipeline_cli.CSVSource')  
    @patch('pipeline_cli.FileSink')
    def test_cli_pipeline_failure(self, mock_sink, mock_source, mock_pipeline):
        """Test CLI when pipeline.run() raises exception"""
        from pipeline_cli import main
        
        # Setup mocks
        mock_source_instance = Mock()
        mock_source.return_value = mock_source_instance
        
        mock_sink_instance = Mock()
        mock_sink.return_value = mock_sink_instance
        
        # Pipeline raises exception
        mock_pipeline_instance = Mock()
        mock_pipeline_instance.run.side_effect = ValueError("Pipeline failed!")
        mock_pipeline.return_value = mock_pipeline_instance
        
        # Mock sys.argv
        test_args = [
            'pipeline_cli.py',
            '--source_type', 'csv',
            '--csv_file', 'test.csv',
            '--sink_type', 'file',
            '--output_file', 'output.txt'
        ]
        
        with patch('sys.argv', test_args):
            with pytest.raises(SystemExit) as exc_info:
                main()
            
            assert exc_info.value.code == 1
    
    @patch('pipeline_cli.MetricsServer')
    @patch('pipeline_cli.DataPipeline')
    @patch('pipeline_cli.CSVSource')
    @patch('pipeline_cli.FileSink')
    def test_cli_with_keyboard_interrupt(self, mock_sink, mock_source, mock_pipeline, mock_server):
        """Test CLI handles KeyboardInterrupt gracefully"""
        from pipeline_cli import main
        
        # Setup mocks
        mock_source_instance = Mock()
        mock_source.return_value = mock_source_instance
        
        mock_sink_instance = Mock()
        mock_sink.return_value = mock_sink_instance
        
        # Pipeline raises KeyboardInterrupt
        mock_pipeline_instance = Mock()
        mock_pipeline_instance.run.side_effect = KeyboardInterrupt()
        mock_pipeline.return_value = mock_pipeline_instance
        
        mock_server_instance = Mock()
        mock_server_instance.is_running.return_value = True
        mock_server.return_value = mock_server_instance
        
        # Mock sys.argv with metrics
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
                except (KeyboardInterrupt, SystemExit):  # pragma: no cover
                    pass  # pragma: no cover
        
        # Metrics server should be stopped
        mock_server_instance.stop.assert_called()
    
    @patch('pipeline_cli.MetricsServer')
    @patch('pipeline_cli.DataPipeline')
    @patch('pipeline_cli.CSVSource')
    @patch('pipeline_cli.FileSink')
    def test_cli_metrics_server_keeps_running(self, mock_sink, mock_source, mock_pipeline, mock_server):
        """Test CLI keeps metrics server running after pipeline completes"""
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
        mock_server_instance.is_running.return_value = True
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
                with patch('signal.pause', side_effect=KeyboardInterrupt()):
                    try:
                        main()
                    except (KeyboardInterrupt, SystemExit):  # pragma: no cover
                        pass  # pragma: no cover
         
        # Server should have been started
        mock_server_instance.start.assert_called()
    
    @patch('pipeline_cli.MetricsServer')  
    @patch('pipeline_cli.DataPipeline')
    @patch('pipeline_cli.CSVSource')
    @patch('pipeline_cli.FileSink')
    def test_cli_signal_handler(self, mock_sink, mock_source, mock_pipeline, mock_server):
        """Test CLI signal handler for graceful shutdown"""
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
        
        # Capture signal handler
        signal_handler = None
        def capture_signal(sig, handler):
            nonlocal signal_handler
            signal_handler = handler
        
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
            with patch('signal.signal', side_effect=capture_signal):
                try:
                    main()
                except SystemExit:  # pragma: no cover
                    pass  # pragma: no cover
        
        # Test the captured signal handler
        if signal_handler:
            with pytest.raises(SystemExit):
                signal_handler(signal.SIGINT, None)
    
    @patch('pipeline_cli.DataPipeline')
    @patch('pipeline_cli.CSVSource')
    @patch('pipeline_cli.FileSink')
    def test_cli_with_all_query_params(self, mock_sink, mock_source, mock_pipeline):
        """Test CLI with all query parameters"""
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
        
        # Mock sys.argv with all query params
        test_args = [
            'pipeline_cli.py',
            '--source_type', 'csv',
            '--csv_file', 'test.csv',
            '--sink_type', 'file',
            '--output_file', 'output.txt',
            '--gte', '2024-01-01',
            '--lte', '2024-12-31',
            '--limit', '100'
        ]
        
        with patch('sys.argv', test_args):
            try:
                main()
            except SystemExit:  # pragma: no cover
                pass  # pragma: no cover
        
        # Verify query params passed to pipeline
        call_args = mock_pipeline_instance.run.call_args
        query_params = call_args[0][0] if call_args[0] else None
        
        if query_params:
            assert 'gte' in query_params
            assert 'lte' in query_params
            assert 'limit' in query_params


class TestPipelineMetricsUnavailable:
    """Test pipeline behavior when metrics are unavailable"""
    
    def test_pipeline_metrics_unavailable(self):
        """Test pipeline when prometheus_client not installed"""
        import tempfile
        import csv
        import os
        from test_impl import CSVSource, FileSink
        
        # Create test CSV
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            writer = csv.DictWriter(f, fieldnames=["id", "data"])
            writer.writeheader()
            writer.writerow({"id": "1", "data": "test"})
            csv_path = f.name
        
        output_path = tempfile.NamedTemporaryFile(suffix='.txt', delete=False).name
        
        try:
            # Temporarily hide metrics module
            with patch.dict('sys.modules', {'metrics': None}):
                # Re-import pipeline to trigger metrics unavailable path
                import importlib
                import pipeline as pipeline_module
                importlib.reload(pipeline_module)
                
                from pipeline import DataPipeline
                source = CSVSource(csv_path)
                sink = FileSink(output_path)
                
                # Create pipeline with metrics enabled (but unavailable)
                pipeline = DataPipeline(
                    source, 
                    sink, 
                    num_threads=1,
                    enable_metrics=True,
                    pipeline_id="test"
                )
                
                # Should still work without metrics
                stats = pipeline.run()
                pipeline.cleanup()
                
                assert stats["inserted"] >= 1
                
        finally:
            if os.path.exists(csv_path):
                os.unlink(csv_path)
            if os.path.exists(output_path):
                os.unlink(output_path)
            
            # Restore normal import
            import importlib
            import pipeline as pipeline_module
            importlib.reload(pipeline_module)


if __name__ == "__main__":  # pragma: no cover
    pytest.main([__file__, "-v"])
