"""
Surgical strike tests - hitting the EXACT remaining 49 lines

Targeting:
- error_analyzer.py: Uncalled handler methods (_json_decode_help, _mysql_error_help, _elasticsearch_error_help)
- test_impl.py: The bare except clause that needs proper exception types

Author: Mac McAllorum (kevin_mcallorum@linux.com)
"""
import pytest
import json
import tempfile
import csv
import os
from error_analyzer import SimpleErrorAnalyzer


class TestErrorAnalyzerHandlerMethods:
    """Test the ACTUAL handler methods in SimpleErrorAnalyzer"""
    
    def test_json_decode_error_handler(self):
        """Test _json_decode_help is called for JSONDecodeError"""
        analyzer = SimpleErrorAnalyzer()
        
        # Create a real JSONDecodeError
        try:
            json.loads("not valid json{{")
        except json.JSONDecodeError as error:
            context = {"operation": "parse_response"}
            result = analyzer.analyze_error(error, context)
            
            assert result is not None
            assert "JSON Decode" in result
            assert "valid JSON" in result
    
    def test_mysql_error_handler_via_module(self):
        """Test _mysql_error_help is called for mysql errors"""
        analyzer = SimpleErrorAnalyzer()
        
        # Create an error that simulates mysql.connector.errors module
        class MySQLError(Exception):
            pass
        
        # Set the module to match the pattern
        error = MySQLError("Access denied for user 'root'@'localhost'")
        error.__class__.__module__ = "mysql.connector.errors.InterfaceError"
        
        context = {"operation": "mysql_connect"}
        result = analyzer.analyze_error(error, context)
        
        assert result is not None
        assert "MySQL" in result
        assert "credentials" in result
    
    def test_elasticsearch_error_handler_via_module(self):
        """Test _elasticsearch_error_help is called for ES errors"""
        analyzer = SimpleErrorAnalyzer()
        
        # Create an error that simulates elasticsearch.exceptions module
        class ESError(Exception):
            pass
        
        error = ESError("ConnectionTimeout")
        error.__class__.__module__ = "elasticsearch.exceptions.ConnectionTimeout"
        
        context = {"operation": "es_search"}
        result = analyzer.analyze_error(error, context)
        
        assert result is not None
        assert "Elasticsearch" in result
        assert "running" in result or "authentication" in result


class TestTestImplExceptionPaths:
    """Test the exception paths in test_impl.py _is_json methods"""
    
    def test_csv_source_is_json_with_invalid_json(self):
        """Trigger the except clause in CSVSource._is_json"""
        from test_impl import CSVSource
        
        # Create CSV with malformed JSON in content
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            writer = csv.DictWriter(f, fieldnames=["id", "content"])
            writer.writeheader()
            # This will fail JSON parsing and hit the except clause
            writer.writerow({"id": "1", "content": "{'not': valid json}"})
            writer.writerow({"id": "2", "content": '{"valid": "json"}'})
            csv_path = f.name
        
        try:
            source = CSVSource(csv_path, content_column="content")
            records = list(source.fetch_records())
            
            # First record should have wrapped the row (invalid JSON)
            # Second record should use the content directly (valid JSON)
            assert len(records) == 2
            
            source.close()
        finally:
            if os.path.exists(csv_path):
                os.unlink(csv_path)
    
    def test_file_sink_is_json_with_invalid_json(self):
        """Trigger the except clause in FileSink._is_json"""
        from test_impl import FileSink
        
        output_path = tempfile.mktemp(suffix='.jsonl')
        
        try:
            sink = FileSink(output_path)
            
            # Insert with content that's not valid JSON (triggers except)
            result1 = sink.insert_record("1", "not json at all")
            assert result1 is True
            
            # Insert with valid JSON
            result2 = sink.insert_record("2", '{"valid": "json"}')
            assert result2 is True
            
            sink.commit()
            sink.close()
            
            # Verify both were written
            with open(output_path, 'r') as f:
                lines = f.readlines()
                assert len(lines) == 2
        
        finally:
            if os.path.exists(output_path):
                os.unlink(output_path)
    
    def test_jsonl_sink_is_json_exception(self):
        """Test JSONLSink exception handling in _is_json equivalent"""
        from test_impl import JSONLSink
        
        output_path = tempfile.mktemp(suffix='.jsonl')
        
        try:
            sink = JSONLSink(output_path)
            
            # Insert with something that will fail json.loads
            result = sink.insert_record("1", "not json")
            assert result is True
            
            sink.commit()
            sink.close()
            
            # Verify it was wrapped in {"raw": ...}
            with open(output_path, 'r') as f:
                line = f.readline()
                record = json.loads(line)
                assert record["id"] == "1"
                assert "raw" in record
        
        finally:
            if os.path.exists(output_path):
                os.unlink(output_path)


class TestRemainingEdgeCases:
    """Hit any remaining edge cases"""
    
    def test_error_analyzer_all_specific_types(self):
        """Test all the specific error types to ensure handlers are called"""
        analyzer = SimpleErrorAnalyzer()
        
        # Test each error type that has a handler
        test_cases = [
            (ConnectionRefusedError("Connection refused"), "Connection Refused"),
            (TimeoutError("Timeout"), "Timeout"),
            (PermissionError("Permission denied"), "Permission"),
            (FileNotFoundError("File not found"), "File Not Found"),
            (KeyError("missing_key"), "Missing Key"),
        ]
        
        for error, expected_text in test_cases:
            result = analyzer.analyze_error(error, {})
            assert result is not None
            assert expected_text in result
    
    def test_csv_source_with_empty_content_column(self):
        """Test CSV where content column is empty (None)"""
        from test_impl import CSVSource
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            writer = csv.DictWriter(f, fieldnames=["id", "content", "extra"])
            writer.writeheader()
            # Empty content - will be None
            writer.writerow({"id": "1", "content": "", "extra": "data"})
            csv_path = f.name
        
        try:
            source = CSVSource(csv_path, content_column="content")
            records = list(source.fetch_records())
            
            assert len(records) == 1
            record_id, content = records[0]
            assert record_id == "1"
            
            # Should have wrapped the full row since content was empty
            parsed = json.loads(content)
            assert "id" in parsed
            
            source.close()
        finally:
            if os.path.exists(csv_path):
                os.unlink(csv_path)
    
    def test_file_sink_duplicate_with_logging(self):
        """Test FileSink with duplicates and logging at intervals"""
        from test_impl import FileSink
        
        output_path = tempfile.mktemp(suffix='.jsonl')
        
        try:
            sink = FileSink(output_path)
            
            # Insert 105 records to trigger logging at 100
            for i in range(105):
                sink.insert_record(str(i), f'{{"data": "test{i}"}}')
            
            # Try duplicates
            sink.insert_record("0", '{"data": "duplicate"}')
            sink.insert_record("1", '{"data": "duplicate"}')
            
            stats = sink.get_stats()
            assert stats["inserted"] == 105
            assert stats["skipped"] == 2
            
            sink.close()
        
        finally:
            if os.path.exists(output_path):
                os.unlink(output_path)


if __name__ == "__main__":  # pragma: no cover
    pytest.main([__file__, "-v"])
