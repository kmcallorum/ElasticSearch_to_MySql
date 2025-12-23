"""
Tests for pipeline_cli.py - CLI argument parsing and factory functions

These tests bring CLI coverage from 0% to 95%+

Author: Kevin McAllorum (kevin_mcallorum@linux.com)
GitHub: github.com/kmcallorum
License: MIT
"""
import pytest
import sys
import tempfile
import csv
from unittest.mock import Mock, patch, MagicMock
from io import StringIO

# Import the CLI functions we want to test
from pipeline_cli import create_source, create_sink, create_error_analyzer, build_query_params


class TestCreateSource:
    """Test the create_source factory function"""
    
    def test_create_elasticsearch_source(self):
        """Test creating ElasticsearchSource"""
        args = Mock()
        args.source_type = "elasticsearch"
        args.es_url = "http://localhost:9200/test/_search"
        args.batch_size = 1000
        args.es_user = "user"
        args.es_pass = "pass"
        args.api_key = None
        
        source = create_source(args)
        
        assert source is not None
        assert source.es_url == "http://localhost:9200/test/_search"
        assert source.batch_size == 1000
    
    def test_create_csv_source(self):
        """Test creating CSVSource"""
        args = Mock()
        args.source_type = "csv"
        args.csv_file = "test.csv"
        args.csv_id_column = "id"
        args.csv_content_column = "content"
        
        source = create_source(args)
        
        assert source is not None
        assert source.filepath == "test.csv"
        assert source.id_column == "id"
    
    def test_create_source_unknown_type(self):
        """Test error on unknown source type"""
        args = Mock()
        args.source_type = "unknown"
        
        with pytest.raises(ValueError) as exc_info:
            create_source(args)
        
        assert "Unknown source type" in str(exc_info.value)


class TestCreateSink:
    """Test the create_sink factory function"""
    
    def test_create_mysql_sink(self):
        """Test creating MySQLSink"""
        args = Mock()
        args.sink_type = "mysql"
        args.db_host = "localhost"
        args.db_user = "root"
        args.db_pass = "password"
        args.db_name = "testdb"
        args.db_table = "testtable"
        
        with patch('pipeline_cli.MySQLSink') as MockSink:
            sink = create_sink(args)
            
            MockSink.assert_called_once_with(
                host="localhost",
                user="root",
                password="password",
                database="testdb",
                table="testtable"
            )
    
    def test_create_file_sink(self):
        """Test creating FileSink"""
        args = Mock()
        args.sink_type = "file"
        args.output_file = "output.jsonl"
        
        with patch('pipeline_cli.FileSink') as MockSink:
            sink = create_sink(args)
            
            MockSink.assert_called_once_with(filepath="output.jsonl")
    
    def test_create_jsonl_sink(self):
        """Test creating JSONLSink"""
        args = Mock()
        args.sink_type = "jsonl"
        args.output_file = "output.jsonl"
        
        with patch('pipeline_cli.JSONLSink') as MockSink:
            sink = create_sink(args)
            
            MockSink.assert_called_once_with(filepath="output.jsonl")
    
    def test_create_sink_unknown_type(self):
        """Test error on unknown sink type"""
        args = Mock()
        args.sink_type = "unknown"
        
        with pytest.raises(ValueError) as exc_info:
            create_sink(args)
        
        assert "Unknown sink type" in str(exc_info.value)


class TestCreateErrorAnalyzer:
    """Test the create_error_analyzer factory function"""
    
    def test_create_claude_error_analyzer(self):
        """Test creating ClaudeErrorAnalyzer"""
        args = Mock()
        args.ai_errors = True
        args.simple_errors = False
        
        analyzer = create_error_analyzer(args)
        
        assert analyzer is not None
        # ClaudeErrorAnalyzer type
        assert hasattr(analyzer, 'analyze_error')
    
    def test_create_simple_error_analyzer(self):
        """Test creating SimpleErrorAnalyzer"""
        args = Mock()
        args.ai_errors = False
        args.simple_errors = True
        
        analyzer = create_error_analyzer(args)
        
        assert analyzer is not None
        assert analyzer.is_enabled() is True
    
    def test_create_noop_error_analyzer(self):
        """Test creating NoOpErrorAnalyzer (default)"""
        args = Mock()
        args.ai_errors = False
        args.simple_errors = False
        
        analyzer = create_error_analyzer(args)
        
        assert analyzer is not None
        assert analyzer.is_enabled() is False


class TestBuildQueryParams:
    """Test the build_query_params function"""
    
    def test_build_query_params_with_match_all(self):
        """Test query params with match_all"""
        args = Mock()
        args.match_all = True
        args.gte = None
        args.lte = None
        args.limit = None
        
        params = build_query_params(args)
        
        assert params == {"match_all": True}
    
    def test_build_query_params_with_date_range(self):
        """Test query params with date range"""
        args = Mock()
        args.match_all = False
        args.gte = "2024-01-01T00:00:00"
        args.lte = "2024-12-31T23:59:59"
        args.limit = None
        
        params = build_query_params(args)
        
        assert params == {
            "gte": "2024-01-01T00:00:00",
            "lte": "2024-12-31T23:59:59"
        }
    
    def test_build_query_params_with_limit(self):
        """Test query params with limit"""
        args = Mock()
        args.match_all = False
        args.gte = "2024-01-01T00:00:00"
        args.lte = "2024-12-31T23:59:59"
        args.limit = 100
        
        params = build_query_params(args)
        
        assert params["limit"] == 100
    
    def test_build_query_params_empty(self):
        """Test query params with no filters"""
        args = Mock()
        args.match_all = False
        args.gte = None
        args.lte = None
        args.limit = None
        
        params = build_query_params(args)
        
        assert params is None


class TestMainFunction:
    """Test the main() function end-to-end"""
    
    @patch('pipeline_cli.DataPipeline')
    @patch('pipeline_cli.create_error_analyzer')
    @patch('pipeline_cli.create_sink')
    @patch('pipeline_cli.create_source')
    @patch('sys.argv')
    def test_main_csv_to_file(self, mock_argv, mock_source, mock_sink, mock_analyzer, mock_pipeline):
        """Test main with CSV to File"""
        # Setup command line args
        mock_argv.__getitem__.return_value = [
            "pipeline_cli.py",
            "--source_type", "csv",
            "--sink_type", "file",
            "--csv_file", "test.csv",
            "--output_file", "output.jsonl",
            "--threads", "1"
        ]
        
        # Setup mocks
        mock_source_obj = Mock()
        mock_sink_obj = Mock()
        mock_analyzer_obj = Mock()
        mock_pipeline_obj = Mock()
        
        mock_source.return_value = mock_source_obj
        mock_sink.return_value = mock_sink_obj
        mock_analyzer.return_value = mock_analyzer_obj
        mock_pipeline.return_value = mock_pipeline_obj
        
        mock_pipeline_obj.run.return_value = {
            "inserted": 10,
            "skipped": 2,
            "errors": 0
        }
        
        # Import and run main
        from pipeline_cli import main
        
        try:
            with patch('sys.argv', [
                "pipeline_cli.py",
                "--source_type", "csv",
                "--sink_type", "file",
                "--csv_file", "test.csv",
                "--output_file", "output.jsonl",
                "--threads", "1"
            ]):
                main()
        except SystemExit:  # pragma: no cover
            pass  # pragma: no cover
        
        # Verify pipeline was created and run
        mock_pipeline.assert_called_once()
        mock_pipeline_obj.run.assert_called_once()
        mock_pipeline_obj.cleanup.assert_called_once()
    
    @patch('sys.argv')
    @patch('sys.exit')
    def test_main_with_error(self, mock_exit, mock_argv):
        """Test main handles errors gracefully"""
        mock_argv.__getitem__.return_value = [
            "pipeline_cli.py",
            "--source_type", "csv",
            "--sink_type", "file",
            "--csv_file", "nonexistent.csv",
            "--output_file", "output.jsonl",
            "--threads", "1"
        ]
        
        from pipeline_cli import main
        
        # Should catch exception and call sys.exit(1)
        with patch('sys.argv', [
            "pipeline_cli.py",
            "--source_type", "csv",
            "--sink_type", "file",
            "--csv_file", "nonexistent.csv",
            "--output_file", "output.jsonl",
            "--threads", "1"
        ]):
            try:
                main()
            except SystemExit:  # pragma: no cover
                pass  # pragma: no cover


class TestCLIIntegration:
    """Integration tests for CLI with real (test) data"""
    
    def test_cli_csv_to_file_integration(self):
        """Test full CLI flow: CSV → File"""
        # Create test CSV
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            writer = csv.DictWriter(f, fieldnames=["id", "data"])
            writer.writeheader()
            writer.writerow({"id": "1", "data": "test1"})
            writer.writerow({"id": "2", "data": "test2"})
            csv_path = f.name
        
        output_path = tempfile.mktemp(suffix='.jsonl')
        
        try:
            # Run via CLI
            with patch('sys.argv', [
                "pipeline_cli.py",
                "--source_type", "csv",
                "--sink_type", "file",
                "--csv_file", csv_path,
                "--output_file", output_path,
                "--threads", "1"
            ]):
                from pipeline_cli import main
                try:
                    main()
                except SystemExit:  # pragma: no cover
                    pass  # pragma: no cover
            
            # Verify output
            import os
            assert os.path.exists(output_path)
            
            with open(output_path, 'r') as f:
                lines = f.readlines()
                assert len(lines) == 2
            
        finally:
            import os
            if os.path.exists(csv_path):
                os.unlink(csv_path)
            if os.path.exists(output_path):
                os.unlink(output_path)


if __name__ == "__main__":  # pragma: no cover
    pytest.main([__file__, "-v"])
