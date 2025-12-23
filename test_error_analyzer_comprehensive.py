"""
Additional tests for error_analyzer.py to hit 100% coverage

These tests specifically target the uncovered error handler methods

Author: Mac McAllorum (kevin_mcallorum@linux.com)
"""
import pytest
import json
from error_analyzer import SimpleErrorAnalyzer


class TestSimpleErrorAnalyzerComprehensive:
    """Comprehensive tests for all SimpleErrorAnalyzer error handlers"""
    
    def test_json_decode_error_help(self):
        """Test JSON decode error handler"""
        analyzer = SimpleErrorAnalyzer()
        
        # Simulate JSONDecodeError
        try:
            json.loads("{'invalid': json}")
        except json.JSONDecodeError as error:
            context = {"operation": "parse_response"}
            result = analyzer.analyze_error(error, context)
            
            assert result is not None
            assert "JSON" in result
            assert "Decode" in result
    
    def test_connection_error_variations(self):
        """Test various connection error messages"""
        analyzer = SimpleErrorAnalyzer()
        
        # Test with generic connection error
        error1 = ConnectionError("Connection refused")
        context1 = {"operation": "database_connect"}
        result1 = analyzer.analyze_error(error1, context1)
        
        assert result1 is not None
        
        # Test with timeout
        error2 = TimeoutError("Connection timed out")
        context2 = {"operation": "database_query"}
        result2 = analyzer.analyze_error(error2, context2)
        
        assert result2 is not None
    
    def test_generic_runtime_error(self):
        """Test generic error handler"""
        analyzer = SimpleErrorAnalyzer()
        
        # Test with a generic runtime error
        error = RuntimeError("Something went wrong")
        context = {"operation": "data_processing"}
        result = analyzer.analyze_error(error, context)
        
        assert result is not None
        assert "RuntimeError" in result
    
    def test_all_error_types_covered(self):
        """Test that all main error types have handlers"""
        analyzer = SimpleErrorAnalyzer()
        
        error_types = [
            (ConnectionRefusedError("refused"), {"operation": "connect"}),
            (TimeoutError("timeout"), {"operation": "fetch"}),
            (PermissionError("denied"), {"operation": "write"}),
            (FileNotFoundError("missing"), {"operation": "read"}),
            (KeyError("missing_key"), {"operation": "parse"}),
        ]
        
        for error, context in error_types:
            result = analyzer.analyze_error(error, context)
            assert result is not None
            assert len(result) > 0


class TestErrorAnalyzerEdgeCases:
    """Test edge cases in error analyzers"""
    
    def test_error_with_empty_context(self):
        """Test error analysis with minimal context"""
        analyzer = SimpleErrorAnalyzer()
        error = ValueError("test error")
        context = {}
        
        result = analyzer.analyze_error(error, context)
        
        assert result is not None
        assert "ValueError" in result
    
    def test_error_with_complex_context(self):
        """Test error analysis with rich context"""
        analyzer = SimpleErrorAnalyzer()
        error = ConnectionRefusedError("Connection refused")
        context = {
            "operation": "mysql_connect",
            "host": "localhost",
            "port": 3306,
            "user": "root",
            "database": "testdb",
            "attempt": 3,
            "total_processed": 1000
        }
        
        result = analyzer.analyze_error(error, context)
        
        assert result is not None
        assert "Connection" in result
    
    def test_nested_exception(self):
        """Test handling of nested exceptions"""
        analyzer = SimpleErrorAnalyzer()
        
        try:
            try:
                raise ValueError("Inner error")
            except ValueError as e:
                raise RuntimeError("Outer error") from e
        except RuntimeError as error:
            context = {"operation": "nested_test"}
            result = analyzer.analyze_error(error, context)
            
            assert result is not None
    
    def test_error_with_special_characters(self):
        """Test error messages with special characters"""
        analyzer = SimpleErrorAnalyzer()
        error = ValueError("Error with 'quotes' and \"double quotes\" and\nnewlines")
        context = {"operation": "parse"}
        
        result = analyzer.analyze_error(error, context)
        
        assert result is not None


if __name__ == "__main__":  # pragma: no cover
    pytest.main([__file__, "-v"])
