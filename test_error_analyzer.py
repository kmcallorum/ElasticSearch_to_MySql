"""
Tests for error analyzer functionality

Author: Kevin McAllorum (kevin_mcallorum@linux.com)
GitHub: github.com/kmcallorum
License: MIT
"""
import pytest
import os
from error_analyzer import (
    NoOpErrorAnalyzer, SimpleErrorAnalyzer, ClaudeErrorAnalyzer
)


class TestNoOpErrorAnalyzer:
    """Test NoOpErrorAnalyzer (default, no analysis)"""
    
    def test_returns_none(self):
        """NoOp analyzer should return None"""
        analyzer = NoOpErrorAnalyzer()
        error = ValueError("test error")
        context = {"operation": "test"}
        
        result = analyzer.analyze_error(error, context)
        assert result is None
    
    def test_is_not_enabled(self):
        """NoOp analyzer should report as disabled"""
        analyzer = NoOpErrorAnalyzer()
        assert analyzer.is_enabled() is False


class TestSimpleErrorAnalyzer:
    """Test SimpleErrorAnalyzer (rule-based)"""
    
    def test_is_enabled(self):
        """Simple analyzer should always be enabled"""
        analyzer = SimpleErrorAnalyzer()
        assert analyzer.is_enabled() is True
    
    def test_connection_refused_help(self):
        """Test connection refused error handling"""
        analyzer = SimpleErrorAnalyzer()
        error = ConnectionRefusedError("Connection refused")
        context = {"operation": "mysql_connect"}
        
        result = analyzer.analyze_error(error, context)
        
        assert result is not None
        assert "Connection Refused" in result
        assert "service is running" in result.lower()
    
    def test_timeout_help(self):
        """Test timeout error handling"""
        analyzer = SimpleErrorAnalyzer()
        error = TimeoutError("Operation timed out")
        context = {"operation": "es_fetch"}
        
        result = analyzer.analyze_error(error, context)
        
        assert result is not None
        assert "Timeout" in result
        assert "network" in result.lower()
    
    def test_permission_help(self):
        """Test permission error handling"""
        analyzer = SimpleErrorAnalyzer()
        error = PermissionError("Permission denied")
        context = {"operation": "file_write"}
        
        result = analyzer.analyze_error(error, context)
        
        assert result is not None
        assert "Permission" in result
        assert "chmod" in result.lower() or "privileges" in result.lower()
    
    def test_file_not_found_help(self):
        """Test file not found error handling"""
        analyzer = SimpleErrorAnalyzer()
        error = FileNotFoundError("test.csv not found")
        context = {"operation": "csv_read"}
        
        result = analyzer.analyze_error(error, context)
        
        assert result is not None
        assert "File Not Found" in result
        assert "path" in result.lower()
    
    def test_key_error_help(self):
        """Test key error handling"""
        analyzer = SimpleErrorAnalyzer()
        error = KeyError("missing_column")
        context = {"operation": "csv_parse"}
        
        result = analyzer.analyze_error(error, context)
        
        assert result is not None
        assert "missing_column" in result
        assert "Key" in result
    
    def test_generic_help_for_unknown_error(self):
        """Test generic help for unrecognized errors"""
        analyzer = SimpleErrorAnalyzer()
        error = RuntimeError("unknown error")
        context = {"operation": "unknown"}
        
        result = analyzer.analyze_error(error, context)
        
        assert result is not None
        assert "RuntimeError" in result


class TestClaudeErrorAnalyzer:
    """Test ClaudeErrorAnalyzer (AI-powered)"""
    
    def test_disabled_without_api_key(self):
        """Analyzer should be disabled without API key"""
        # Temporarily clear env var
        old_key = os.environ.get("ANTHROPIC_API_KEY")
        if old_key:
            del os.environ["ANTHROPIC_API_KEY"] # pragma: no cover
        
        analyzer = ClaudeErrorAnalyzer()
        
        assert analyzer.is_enabled() is False
        
        # Restore env var
        if old_key:
            os.environ["ANTHROPIC_API_KEY"] = old_key # pragma: no cover
    
    def test_enabled_with_api_key(self):
        """Analyzer should be enabled with API key"""
        analyzer = ClaudeErrorAnalyzer(api_key="test-key-123")
        assert analyzer.is_enabled() is True
    
    def test_returns_none_when_disabled(self):
        """Should return None when no API key"""
        old_key = os.environ.get("ANTHROPIC_API_KEY")
        if old_key:
            del os.environ["ANTHROPIC_API_KEY"] # pragma: no cover
        
        analyzer = ClaudeErrorAnalyzer()
        error = ValueError("test")
        context = {"operation": "test"}
        
        result = analyzer.analyze_error(error, context)
        assert result is None
        
        if old_key:
            os.environ["ANTHROPIC_API_KEY"] = old_key # pragma: no cover
    
    def test_builds_proper_prompt(self):
        """Test that prompt is built correctly"""
        analyzer = ClaudeErrorAnalyzer(api_key="test-key")
        
        error = ValueError("Invalid data")
        context = {"operation": "data_parse", "record_id": "123"}
        
        prompt = analyzer._build_prompt(
            "ValueError",
            "Invalid data",
            "Traceback...",
            context
        )
        
        assert "ValueError" in prompt
        assert "Invalid data" in prompt
        assert "data_parse" in prompt
        assert "record_id" in prompt
        assert "Troubleshooting" in prompt


class TestErrorAnalyzerIntegration:
    """Integration tests with pipeline"""
    
    def test_noop_analyzer_in_pipeline(self):
        """Test that NoOp analyzer doesn't break pipeline"""
        from pipeline import DataPipeline
        from test_impl import CSVSource, FileSink
        import tempfile
        import csv
        
        # Create test CSV
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            writer = csv.DictWriter(f, fieldnames=["id", "data"])
            writer.writeheader()
            writer.writerow({"id": "1", "data": "test"})
            csv_path = f.name
        
        # Create output path
        output_path = tempfile.NamedTemporaryFile(suffix='.jsonl', delete=False).name
        
        try:
            source = CSVSource(csv_path)
            sink = FileSink(output_path)
            analyzer = NoOpErrorAnalyzer()
            
            pipeline = DataPipeline(source, sink, num_threads=1, error_analyzer=analyzer)
            stats = pipeline.run()
            pipeline.cleanup()
            
            assert stats["inserted"] == 1
            
        finally:
            if os.path.exists(csv_path):
                os.unlink(csv_path)
            if os.path.exists(output_path):
                os.unlink(output_path)
    
    def test_simple_analyzer_in_pipeline(self):
        """Test that Simple analyzer works in pipeline"""
        from pipeline import DataPipeline
        from test_impl import CSVSource, FileSink
        import tempfile
        import csv
        
        # Create test CSV
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            writer = csv.DictWriter(f, fieldnames=["id", "data"])
            writer.writeheader()
            writer.writerow({"id": "1", "data": "test"})
            csv_path = f.name
        
        output_path = tempfile.NamedTemporaryFile(suffix='.jsonl', delete=False).name
        
        try:
            source = CSVSource(csv_path)
            sink = FileSink(output_path)
            analyzer = SimpleErrorAnalyzer()
            
            pipeline = DataPipeline(source, sink, num_threads=1, error_analyzer=analyzer)
            stats = pipeline.run()
            pipeline.cleanup()
            
            assert stats["inserted"] == 1
            assert analyzer.is_enabled() is True
            
        finally:
            if os.path.exists(csv_path):
                os.unlink(csv_path)
            if os.path.exists(output_path):
                os.unlink(output_path)


if __name__ == "__main__":  # pragma: no cover
    pytest.main([__file__, "-v"])
