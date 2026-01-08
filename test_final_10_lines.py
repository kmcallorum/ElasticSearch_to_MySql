"""
THE FINAL 10 LINES - test_impl.py edge cases

Covers:
1. Duplicate ID handling in JSONLSink
2. Exception handlers in FileSink
3. Exception handlers in JSONLSink

Author: Kevin McAllorum
"""
import pytest
import tempfile
import os
from unittest.mock import patch
from test_impl import FileSink, JSONLSink


class TestFileSinkExceptionHandler:
    """Test the exception handler in FileSink.insert_record"""
    
    def test_file_sink_write_exception(self):
        """Trigger exception handler when file.write() fails"""
        output_path = tempfile.NamedTemporaryFile(suffix='.jsonl', delete=False).name
        
        try:
            sink = FileSink(output_path)
            
            # Close the file to make writes fail
            sink.file.close()
            
            # Now try to insert - should trigger exception handler
            result = sink.insert_record("1", '{"data": "test"}')
            
            # Should return False and increment errors
            assert result is False
            stats = sink.get_stats()
            assert stats["errors"] == 1
            
            print("✅ FileSink exception handler covered!")
            
        finally:
            if os.path.exists(output_path):
                os.unlink(output_path)
    
    def test_file_sink_write_fails_with_bad_data(self):
        """Test FileSink when json.dumps fails"""
        output_path = tempfile.NamedTemporaryFile(suffix='.jsonl', delete=False).name
        
        try:
            sink = FileSink(output_path)
            
            # Mock json.dumps to raise an exception
            with patch('test_impl.json.dumps', side_effect=TypeError("Cannot serialize")):
                result = sink.insert_record("1", '{"data": "test"}')
                
                assert result is False
                stats = sink.get_stats()
                assert stats["errors"] == 1
            
            sink.close()
            print("✅ FileSink json.dumps exception covered!")
            
        finally:
            if os.path.exists(output_path):
                os.unlink(output_path)


class TestJSONLSinkDuplicatesAndExceptions:
    """Test duplicate handling and exception handler in JSONLSink"""
    
    def test_jsonl_sink_duplicate_ids(self):
        """Test duplicate ID handling in JSONLSink (lines 165-167)"""
        output_path = tempfile.NamedTemporaryFile(suffix='.jsonl', delete=False).name
        
        try:
            sink = JSONLSink(output_path)
            
            # Insert record with ID "1"
            result1 = sink.insert_record("1", '{"data": "first"}')
            assert result1 is True
            
            # Try to insert duplicate ID "1" - should skip
            result2 = sink.insert_record("1", '{"data": "duplicate"}')
            assert result2 is False  # Returns False for duplicate
            
            # Check stats
            stats = sink.get_stats()
            assert stats["inserted"] == 1
            assert stats["skipped"] == 1  # Duplicate was skipped!
            
            sink.close()
            print("✅ JSONLSink duplicate ID handling covered!")
            
        finally:
            if os.path.exists(output_path):
                os.unlink(output_path)
    
    def test_jsonl_sink_write_exception(self):
        """Trigger exception handler when file.write() fails"""
        output_path = tempfile.NamedTemporaryFile(suffix='.jsonl', delete=False).name
        
        try:
            sink = JSONLSink(output_path)
            
            # Close the file to make writes fail
            sink.file.close()
            
            # Now try to insert - should trigger exception handler (lines 182-185)
            result = sink.insert_record("1", '{"data": "test"}')
            
            # Should return False and increment errors
            assert result is False
            stats = sink.get_stats()
            assert stats["errors"] == 1
            
            print("✅ JSONLSink exception handler covered!")
            
        finally:
            if os.path.exists(output_path):
                os.unlink(output_path)
    
    def test_jsonl_sink_json_dumps_fails(self):
        """Test JSONLSink when json.dumps fails"""
        output_path = tempfile.NamedTemporaryFile(suffix='.jsonl', delete=False).name
        
        try:
            sink = JSONLSink(output_path)
            
            # Mock json.dumps to raise an exception
            with patch('test_impl.json.dumps', side_effect=TypeError("Cannot serialize")):
                result = sink.insert_record("1", '{"data": "test"}')
                
                assert result is False
                stats = sink.get_stats()
                assert stats["errors"] == 1
            
            sink.close()
            print("✅ JSONLSink json.dumps exception covered!")
            
        finally:
            if os.path.exists(output_path):
                os.unlink(output_path)


if __name__ == "__main__":  # pragma: no cover
    pytest.main([__file__, "-v", "-s"])
