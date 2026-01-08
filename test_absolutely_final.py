"""
ABSOLUTELY GUARANTEED handler tests for error_analyzer.py

These tests DIRECTLY call the handler methods to ensure 100% coverage.
"""
import pytest
import json
from error_analyzer import SimpleErrorAnalyzer


class TestErrorAnalyzerHandlersDirectly:
    """Test by directly calling the handler methods"""
    
    def test_json_decode_help_called(self):
        """DIRECTLY trigger _json_decode_help"""
        analyzer = SimpleErrorAnalyzer()
        
        # Create real JSONDecodeError
        try:
            json.loads("{invalid json")
        except json.JSONDecodeError as error:
            # This MUST call _json_decode_help because error_type is "JSONDecodeError"
            result = analyzer.analyze_error(error, {"operation": "test"})
            
            # Verify it was called by checking output
            assert result is not None
            assert "JSON Decode" in result
            assert "valid json" in result.lower()  # Fixed: lowercase
            print(f"✅ JSON handler called! Result length: {len(result)}")
    
    def test_mysql_help_via_module_pattern(self):
        """Trigger _mysql_error_help via module pattern matching"""
        analyzer = SimpleErrorAnalyzer()
        
        # Create custom error with mysql module
        class MockMySQLError(Exception):
            pass
        
        error = MockMySQLError("Access denied")
        # Set module to match pattern
        MockMySQLError.__module__ = "mysql.connector.errors.ProgrammingError"
        
        result = analyzer.analyze_error(error, {"operation": "test"})
        
        assert result is not None
        assert "MySQL" in result
        assert "credentials" in result.lower()
        print(f"✅ MySQL handler called! Result length: {len(result)}")
    
    def test_elasticsearch_help_via_module_pattern(self):
        """Trigger _elasticsearch_error_help via module pattern matching"""
        analyzer = SimpleErrorAnalyzer()
        
        # Create custom error with ES module
        class MockESError(Exception):
            pass
        
        error = MockESError("Connection timeout")
        # Set module to match pattern
        MockESError.__module__ = "elasticsearch.exceptions.ConnectionError"
        
        result = analyzer.analyze_error(error, {"operation": "test"})
        
        assert result is not None
        assert "Elasticsearch" in result
        assert ("running" in result.lower() or "authentication" in result.lower())
        print(f"✅ ES handler called! Result length: {len(result)}")
    
    def test_all_handler_methods_get_called(self):
        """Ensure ALL handler methods are exercised"""
        analyzer = SimpleErrorAnalyzer()
        
        # Test each handler's error type
        test_cases = [
            (ConnectionRefusedError("refused"), "Connection Refused"),
            (TimeoutError("timeout"), "Timeout"),
            (PermissionError("denied"), "Permission"),
            (FileNotFoundError("missing"), "File Not Found"),
            (KeyError("missing_key"), "Missing Key"),
        ]
        
        for error, expected in test_cases:
            result = analyzer.analyze_error(error, {})
            assert result is not None
            assert expected in result
            print(f"✅ Handler for {type(error).__name__} worked!")


class TestTestImplExceptionBranches:
    """Test exception branches in test_impl.py"""
    
    def test_csv_source_invalid_json_exception(self):
        """Test CSVSource._is_json exception path"""
        from test_impl import CSVSource
        import tempfile
        import csv
        import os
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            writer = csv.DictWriter(f, fieldnames=["id", "content"])
            writer.writeheader()
            writer.writerow({"id": "1", "content": "not json"})
            csv_path = f.name
        
        try:
            source = CSVSource(csv_path, content_column="content")
            records = list(source.fetch_records())
            assert len(records) == 1
            source.close()
            print("✅ CSVSource exception path covered!")
        finally:
            if os.path.exists(csv_path):
                os.unlink(csv_path)
    
    def test_file_sink_invalid_json_exception(self):
        """Test FileSink._is_json exception path"""
        from test_impl import FileSink
        import tempfile
        import os
        
        output_path = tempfile.NamedTemporaryFile(suffix='.jsonl', delete=False).name
        
        try:
            sink = FileSink(output_path)
            result = sink.insert_record("1", "not json")
            assert result is True
            sink.close()
            print("✅ FileSink exception path covered!")
        finally:
            if os.path.exists(output_path):
                os.unlink(output_path)
    
    def test_jsonl_sink_invalid_json_exception(self):
        """Test JSONLSink exception path"""
        from test_impl import JSONLSink
        import tempfile
        import os
        
        output_path = tempfile.NamedTemporaryFile(suffix='.jsonl', delete=False).name
        
        try:
            sink = JSONLSink(output_path)
            result = sink.insert_record("1", "not json")
            assert result is True
            sink.close()
            
            # Verify it wrapped in {"raw": ...}
            with open(output_path, 'r') as f:
                line = f.readline()
                record = json.loads(line)
                assert "raw" in record
            
            print("✅ JSONLSink exception path covered!")
        finally:
            if os.path.exists(output_path):
                os.unlink(output_path)


if __name__ == "__main__":  # pragma: no cover
    pytest.main([__file__, "-v", "-s"])  # -s shows print statements
