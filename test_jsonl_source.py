"""
Comprehensive tests for JSONLSource to achieve 100% coverage

Author: Mac McAllorum
"""
import pytest
import json
import tempfile
import os
from jsonl_source import JSONLSource


class TestJSONLSourceBasics:
    """Test basic functionality of JSONLSource"""
    
    def test_initialization_default_fields(self):
        """Test JSONLSource initialization with default field names"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False) as f:
            f.write('{"id": "1", "content": {"data": "test"}}\n')
            temp_file = f.name
        
        try:
            source = JSONLSource(temp_file)
            assert source.filepath == temp_file
            assert source.id_field == 'id'
            assert source.content_field == 'content'
            assert source.records_read == 0
        finally:
            os.unlink(temp_file)
    
    def test_initialization_custom_fields(self):
        """Test JSONLSource initialization with custom field names"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False) as f:
            f.write('{"doc_id": "1", "data": {"info": "test"}}\n')
            temp_file = f.name
        
        try:
            source = JSONLSource(temp_file, id_field='doc_id', content_field='data')
            assert source.id_field == 'doc_id'
            assert source.content_field == 'data'
        finally:
            os.unlink(temp_file)
    
    def test_fetch_records_basic(self):
        """Test fetching records with standard id/content fields"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False) as f:
            f.write('{"id": "rec1", "content": {"name": "Alice"}}\n')
            f.write('{"id": "rec2", "content": {"name": "Bob"}}\n')
            f.write('{"id": "rec3", "content": {"name": "Charlie"}}\n')
            temp_file = f.name
        
        try:
            source = JSONLSource(temp_file)
            records = list(source.fetch_records())
            
            assert len(records) == 3
            assert records[0][0] == "rec1"
            assert records[0][1] == {"name": "Alice"}
            assert records[1][0] == "rec2"
            assert records[2][0] == "rec3"
            assert source.records_read == 3
        finally:
            os.unlink(temp_file)
    
    def test_fetch_records_with_limit(self):
        """Test fetching records with limit parameter"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False) as f:
            for i in range(10):
                f.write(f'{{"id": "rec{i}", "content": {{"num": {i}}}}}\n')
            temp_file = f.name
        
        try:
            source = JSONLSource(temp_file)
            records = list(source.fetch_records({'limit': 5}))
            
            assert len(records) == 5
            assert source.records_read == 5
        finally:
            os.unlink(temp_file)
    
    def test_fetch_records_custom_fields(self):
        """Test fetching with custom id and content field names"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False) as f:
            f.write('{"doc_id": "d1", "payload": {"info": "test1"}}\n')
            f.write('{"doc_id": "d2", "payload": {"info": "test2"}}\n')
            temp_file = f.name
        
        try:
            source = JSONLSource(temp_file, id_field='doc_id', content_field='payload')
            records = list(source.fetch_records())
            
            assert len(records) == 2
            assert records[0][0] == "d1"
            assert records[0][1] == {"info": "test1"}
            assert records[1][0] == "d2"
        finally:
            os.unlink(temp_file)
    
    def test_fetch_records_missing_id_field(self):
        """Test fetching when ID field is missing - should generate ID from line number"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False) as f:
            f.write('{"content": {"name": "Alice"}}\n')
            f.write('{"content": {"name": "Bob"}}\n')
            temp_file = f.name
        
        try:
            source = JSONLSource(temp_file)
            records = list(source.fetch_records())
            
            assert len(records) == 2
            assert records[0][0] == "line_1"  # Generated ID
            assert records[1][0] == "line_2"
        finally:
            os.unlink(temp_file)
    
    def test_fetch_records_entire_record_as_content(self):
        """Test when content_field is None - entire record becomes content"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False) as f:
            f.write('{"id": "1", "name": "Alice", "age": 30}\n')
            f.write('{"id": "2", "name": "Bob", "age": 25}\n')
            temp_file = f.name
        
        try:
            source = JSONLSource(temp_file, content_field=None)
            records = list(source.fetch_records())
            
            assert len(records) == 2
            assert records[0][0] == "1"
            assert records[0][1] == {"id": "1", "name": "Alice", "age": 30}
            assert records[1][1] == {"id": "2", "name": "Bob", "age": 25}
        finally:
            os.unlink(temp_file)
    
    def test_fetch_records_missing_content_field(self):
        """Test when specified content_field doesn't exist - uses entire record"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False) as f:
            f.write('{"id": "1", "data": {"value": 100}}\n')
            temp_file = f.name
        
        try:
            source = JSONLSource(temp_file, content_field='nonexistent')
            records = list(source.fetch_records())
            
            assert len(records) == 1
            assert records[0][1] == {"id": "1", "data": {"value": 100}}
        finally:
            os.unlink(temp_file)
    
    def test_close(self):
        """Test close method"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False) as f:
            f.write('{"id": "1", "content": {}}\n')
            temp_file = f.name
        
        try:
            source = JSONLSource(temp_file)
            list(source.fetch_records())
            source.close()
            # Should not raise any errors
            assert source.records_read == 1
        finally:
            os.unlink(temp_file)


class TestJSONLSourceEdgeCases:
    """Test edge cases and error handling"""
    
    def test_empty_file(self):
        """Test reading empty JSONL file"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False) as f:
            # Write nothing
            temp_file = f.name
        
        try:
            source = JSONLSource(temp_file)
            records = list(source.fetch_records())
            
            assert len(records) == 0
            assert source.records_read == 0
        finally:
            os.unlink(temp_file)
    
    def test_file_with_empty_lines(self):
        """Test file with empty lines (should be skipped)"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False) as f:
            f.write('{"id": "1", "content": {"a": 1}}\n')
            f.write('\n')  # Empty line
            f.write('   \n')  # Whitespace only
            f.write('{"id": "2", "content": {"a": 2}}\n')
            temp_file = f.name
        
        try:
            source = JSONLSource(temp_file)
            records = list(source.fetch_records())
            
            assert len(records) == 2
            assert records[0][0] == "1"
            assert records[1][0] == "2"
        finally:
            os.unlink(temp_file)
    
    def test_invalid_json_line(self):
        """Test handling of invalid JSON line (should be skipped with error log)"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False) as f:
            f.write('{"id": "1", "content": {"valid": true}}\n')
            f.write('{"id": "2", "invalid json here\n')  # Invalid JSON
            f.write('{"id": "3", "content": {"valid": true}}\n')
            temp_file = f.name
        
        try:
            source = JSONLSource(temp_file)
            records = list(source.fetch_records())
            
            # Should skip the invalid line
            assert len(records) == 2
            assert records[0][0] == "1"
            assert records[1][0] == "3"
            assert source.records_read == 2
        finally:
            os.unlink(temp_file)
    
    def test_file_not_found(self):
        """Test FileNotFoundError is raised for non-existent file"""
        source = JSONLSource('/nonexistent/path/file.jsonl')
        
        with pytest.raises(FileNotFoundError):
            list(source.fetch_records())
    
    def test_limit_zero(self):
        """Test with limit of 0 - treats as no limit (reads all records)"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False) as f:
            f.write('{"id": "1", "content": {}}\n')
            f.write('{"id": "2", "content": {}}\n')
            temp_file = f.name
        
        try:
            source = JSONLSource(temp_file)
            records = list(source.fetch_records({'limit': 0}))
            
            assert len(records) == 2
            assert source.records_read == 2
        finally:
            os.unlink(temp_file)
    
    def test_limit_exceeds_file_size(self):
        """Test when limit is larger than file - should read all records"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False) as f:
            f.write('{"id": "1", "content": {}}\n')
            f.write('{"id": "2", "content": {}}\n')
            temp_file = f.name
        
        try:
            source = JSONLSource(temp_file)
            records = list(source.fetch_records({'limit': 100}))
            
            assert len(records) == 2
            assert source.records_read == 2
        finally:
            os.unlink(temp_file)
    
    def test_complex_nested_json(self):
        """Test with complex nested JSON structures"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False) as f:
            complex_data = {
                "id": "complex1",
                "content": {
                    "nested": {
                        "deep": {
                            "structure": {
                                "with": ["arrays", "and", "objects"],
                                "numbers": [1, 2, 3],
                                "boolean": True,
                                "null": None
                            }
                        }
                    }
                }
            }
            f.write(json.dumps(complex_data) + '\n')
            temp_file = f.name
        
        try:
            source = JSONLSource(temp_file)
            records = list(source.fetch_records())
            
            assert len(records) == 1
            assert records[0][0] == "complex1"
            assert records[0][1]["nested"]["deep"]["structure"]["with"] == ["arrays", "and", "objects"]
        finally:
            os.unlink(temp_file)
    
    def test_unicode_content(self):
        """Test handling of Unicode characters"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False, encoding='utf-8') as f:
            f.write('{"id": "unicode1", "content": {"text": "Hello 世界 🌍 café"}}\n')
            temp_file = f.name
        
        try:
            source = JSONLSource(temp_file)
            records = list(source.fetch_records())
            
            assert len(records) == 1
            assert "世界" in records[0][1]["text"]
            assert "🌍" in records[0][1]["text"]
            assert "café" in records[0][1]["text"]
        finally:
            os.unlink(temp_file)
    
    def test_large_record(self):
        """Test handling of large records"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False) as f:
            large_content = {"data": "x" * 10000}  # 10KB of data
            f.write(json.dumps({"id": "large1", "content": large_content}) + '\n')
            temp_file = f.name
        
        try:
            source = JSONLSource(temp_file)
            records = list(source.fetch_records())
            
            assert len(records) == 1
            assert len(records[0][1]["data"]) == 10000
        finally:
            os.unlink(temp_file)
    
    def test_multiple_fetch_calls(self):
        """Test that multiple fetch_records calls work correctly"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False) as f:
            f.write('{"id": "1", "content": {}}\n')
            f.write('{"id": "2", "content": {}}\n')
            temp_file = f.name
        
        try:
            source = JSONLSource(temp_file)
            
            # First fetch
            records1 = list(source.fetch_records())
            assert len(records1) == 2
            
            # Second fetch (should read from beginning again)
            records2 = list(source.fetch_records())
            assert len(records2) == 2
            
            # Total count should be cumulative
            assert source.records_read == 4
        finally:
            os.unlink(temp_file)
    
    def test_query_params_none(self):
        """Test passing None as query_params"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False) as f:
            f.write('{"id": "1", "content": {}}\n')
            temp_file = f.name
        
        try:
            source = JSONLSource(temp_file)
            records = list(source.fetch_records(None))
            
            assert len(records) == 1
        finally:
            os.unlink(temp_file)
    
    def test_query_params_empty_dict(self):
        """Test passing empty dict as query_params"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False) as f:
            f.write('{"id": "1", "content": {}}\n')
            temp_file = f.name
        
        try:
            source = JSONLSource(temp_file)
            records = list(source.fetch_records({}))
            
            assert len(records) == 1
        finally:
            os.unlink(temp_file)

    def test_file_permission_error(self):
        """Test handling of file permission errors (generic Exception path)"""
        import stat
        with tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False) as f:
            f.write('{"id": "1", "content": {}}\n')
            temp_file = f.name

        try:
            # Remove read permissions
            os.chmod(temp_file, 0o000)

            source = JSONLSource(temp_file)

            # Should raise PermissionError (caught by generic Exception handler)
            with pytest.raises(Exception):  # Could be PermissionError or OSError
                list(source.fetch_records())
        finally:
            # Restore permissions before cleanup
            try:
                os.chmod(temp_file, stat.S_IRUSR | stat.S_IWUSR)
                os.unlink(temp_file)
            except OSError:  # pragma: no cover
                pass  # pragma: no cover

class TestJSONLSourceIntegration:
    """Integration tests matching real usage patterns"""
    
    def test_real_world_elasticsearch_format(self):
        """Test with realistic Elasticsearch-style documents"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False) as f:
            # Realistic ES document structure
            doc = {
                "id": "____ES_RECORD_00001",
                "content": {
                    "@version": "1",
                    "@timestamp": "2021-01-05T10:02:44.964Z",
                    "eventData": {
                        "type": "pipeline.quality_scan.fortify",
                        "status": "success",
                        "duration_ms": 150
                    },
                    "fortifyData": {
                        "scanType": "full",
                        "fortifyIssues": "Critical-102/High-21/Medium-6/Low:1553"
                    }
                }
            }
            f.write(json.dumps(doc) + '\n')
            temp_file = f.name
        
        try:
            source = JSONLSource(temp_file)
            records = list(source.fetch_records())
            
            assert len(records) == 1
            assert records[0][0] == "____ES_RECORD_00001"
            assert records[0][1]["eventData"]["type"] == "pipeline.quality_scan.fortify"
            assert records[0][1]["fortifyData"]["scanType"] == "full"
        finally:
            os.unlink(temp_file)
    
    def test_schema_driven_test_data(self):
        """Test with generated schema-driven test data format"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False) as f:
            for i in range(5):
                doc = {
                    "id": f"____ES_RECORD_{i:05d}",
                    "content": {
                        "@version": "1",
                        "eventData": {
                            "status": "success" if i % 2 == 0 else "failure",
                            "duration_ms": 100 + i * 50
                        }
                    }
                }
                f.write(json.dumps(doc) + '\n')
            temp_file = f.name
        
        try:
            source = JSONLSource(temp_file)
            records = list(source.fetch_records())
            
            assert len(records) == 5
            # Verify variation in data
            statuses = [r[1]["eventData"]["status"] for r in records]
            assert "success" in statuses
            assert "failure" in statuses
        finally:
            os.unlink(temp_file)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
