"""
Additional comprehensive tests for error_analyzer.py to achieve 100% coverage

Author: Mac McAllorum  
"""
import pytest
import os
from unittest.mock import Mock, patch, MagicMock
from error_analyzer import (
    ClaudeErrorAnalyzer,
    SimpleErrorAnalyzer
)


class TestClaudeErrorAnalyzerComprehensive:
    """Comprehensive tests for ClaudeErrorAnalyzer to achieve full coverage"""
    
    def test_analyze_errors_method(self):
        """Test the analyze_errors() method for aggregate error analysis"""
        # Mock the environment and anthropic client
        with patch.dict(os.environ, {'ANTHROPIC_API_KEY': 'test-key'}):
            with patch('anthropic.Anthropic') as mock_anthropic_class:
                # Setup mock
                mock_client = Mock()
                mock_message = Mock()
                mock_message.content = [Mock(text="AI analysis result")]
                mock_client.messages.create.return_value = mock_message
                mock_anthropic_class.return_value = mock_client
                
                analyzer = ClaudeErrorAnalyzer()
                
                # Call analyze_errors
                result = analyzer.analyze_errors(
                    operation="pipeline_execution",
                    error_count=100,
                    context={
                        "source_type": "jsonl",
                        "sink_type": "mysql",
                        "success_rate": "0%"
                    }
                )
                
                assert result == "AI analysis result"
                assert mock_client.messages.create.called
    
    def test_analyze_errors_no_api_key(self):
        """Test analyze_errors when API key is not set"""
        with patch.dict(os.environ, {}, clear=True):
            analyzer = ClaudeErrorAnalyzer(api_key="temp-key")  # Give it a key for init
            
            # Temporarily remove the key
            with patch.dict(os.environ, {}, clear=True):
                result = analyzer.analyze_errors(
                    operation="test",
                    error_count=10,
                    context={}
                )
                
                assert "ANTHROPIC_API_KEY environment variable not set" in result
    
    def test_analyze_errors_api_failure(self):
        """Test analyze_errors when API call fails"""
        with patch.dict(os.environ, {'ANTHROPIC_API_KEY': 'test-key'}):
            with patch('anthropic.Anthropic') as mock_anthropic_class:
                # Setup mock client that raises exception on messages.create
                mock_client = Mock()
                mock_client.messages.create.side_effect = Exception("API Error")
                mock_anthropic_class.return_value = mock_client
                
                analyzer = ClaudeErrorAnalyzer()
                
                result = analyzer.analyze_errors(
                    operation="test",
                    error_count=5,
                    context={}
                )
                
                assert "AI analysis failed" in result
                assert "API Error" in result
    
    def test_build_prompt_method(self):
        """Test _build_prompt() method"""
        with patch.dict(os.environ, {'ANTHROPIC_API_KEY': 'test-key'}):
            analyzer = ClaudeErrorAnalyzer()
            
            prompt = analyzer._build_prompt(
                error_type="ValueError",
                error_message="Invalid value",
                error_traceback="Traceback...",
                context={"operation": "insert", "record_id": "123"}
            )
            
            assert "ValueError" in prompt
            assert "Invalid value" in prompt
            assert "Traceback" in prompt
            assert "insert" in prompt
            assert "🤖 AI Troubleshooting Suggestions:" in prompt
    
    def test_call_claude_api_success(self):
        """Test _call_claude_api() with successful call"""
        with patch.dict(os.environ, {'ANTHROPIC_API_KEY': 'test-key'}):
            with patch('anthropic.Anthropic') as mock_anthropic_class:
                # Setup mock
                mock_client = Mock()
                mock_message = Mock()
                mock_message.content = [Mock(text="Suggestion text")]
                mock_client.messages.create.return_value = mock_message
                mock_anthropic_class.return_value = mock_client
                
                analyzer = ClaudeErrorAnalyzer()
                
                result = analyzer._call_claude_api("Test prompt")
                
                assert result == "Suggestion text"
                mock_client.messages.create.assert_called_once()
    
    def test_call_claude_api_import_error(self):
        """Test _call_claude_api() when anthropic package not installed"""
        with patch.dict(os.environ, {'ANTHROPIC_API_KEY': 'test-key'}):
            analyzer = ClaudeErrorAnalyzer()
            
            # Mock the import to raise ImportError
            import builtins
            real_import = builtins.__import__
            
            def mock_import(name, *args, **kwargs):
                if name == 'anthropic':
                    raise ImportError("No module named 'anthropic'")
                return real_import(name, *args, **kwargs)
            
            with patch('builtins.__import__', side_effect=mock_import):
                result = analyzer._call_claude_api("Test prompt")
                
                assert "anthropic' package not installed" in result
    
    def test_call_claude_api_generic_exception(self):
        """Test _call_claude_api() with generic API exception"""
        with patch.dict(os.environ, {'ANTHROPIC_API_KEY': 'test-key'}):
            with patch('anthropic.Anthropic') as mock_anthropic_class:
                # Setup mock client that raises exception on messages.create
                mock_client = Mock()
                mock_client.messages.create.side_effect = Exception("API call failed")
                mock_anthropic_class.return_value = mock_client
                
                analyzer = ClaudeErrorAnalyzer()
                
                result = analyzer._call_claude_api("Test prompt")
                
                assert "AI analysis failed" in result
                assert "API call failed" in result
    
    def test_analyze_error_disabled(self):
        """Test analyze_error when analyzer is disabled"""
        # Create analyzer without API key
        with patch.dict(os.environ, {}, clear=True):
            analyzer = ClaudeErrorAnalyzer()
            
            error = ValueError("test")
            result = analyzer.analyze_error(error, {"operation": "test"})
            
            assert result is None
    
    def test_analyze_error_with_exception(self):
        """Test analyze_error when analysis itself fails"""
        with patch.dict(os.environ, {'ANTHROPIC_API_KEY': 'test-key'}):
            analyzer = ClaudeErrorAnalyzer()
            
            # Make _build_prompt raise exception
            with patch.object(analyzer, '_build_prompt', side_effect=Exception("Build failed")):
                error = ValueError("test")
                result = analyzer.analyze_error(error, {"operation": "test"})
                
                # Should return None and log error
                assert result is None


class TestSimpleErrorAnalyzerAllMethods:
    """Test all helper methods in SimpleErrorAnalyzer for complete coverage"""
    
    def test_timeout_help(self):
        """Test _timeout_help method"""
        analyzer = SimpleErrorAnalyzer()
        error = TimeoutError("Timeout")
        context = {"operation": "query"}
        
        result = analyzer.analyze_error(error, context)
        
        assert result is not None
        assert "Timeout" in result
        assert "network connectivity" in result
    
    def test_permission_help(self):
        """Test _permission_help method"""
        analyzer = SimpleErrorAnalyzer()
        error = PermissionError("Permission denied")
        context = {"operation": "file_write"}
        
        result = analyzer.analyze_error(error, context)
        
        assert result is not None
        assert "Permission Denied" in result
        assert "ls -la" in result
    
    def test_file_not_found_help(self):
        """Test _file_not_found_help method"""
        analyzer = SimpleErrorAnalyzer()
        error = FileNotFoundError("File not found")
        context = {"operation": "read_file"}
        
        result = analyzer.analyze_error(error, context)
        
        assert result is not None
        assert "File Not Found" in result
        assert "file path" in result
    
    def test_json_decode_help(self):
        """Test _json_decode_help method"""
        analyzer = SimpleErrorAnalyzer()
        
        # Create a JSONDecodeError
        import json
        try:
            json.loads("invalid json")
        except json.JSONDecodeError as e:
            error = e
        
        context = {"operation": "parse_json"}
        result = analyzer.analyze_error(error, context)
        
        assert result is not None
        assert "JSON Decode Error" in result
        assert "valid JSON" in result
    
    def test_key_error_help(self):
        """Test _key_error_help method"""
        analyzer = SimpleErrorAnalyzer()
        error = KeyError("missing_field")
        context = {"operation": "extract_field"}
        
        result = analyzer.analyze_error(error, context)
        
        assert result is not None
        assert "Missing Key" in result
        assert "missing_field" in result
        assert "data structure" in result
    
    def test_mysql_error_help(self):
        """Test _mysql_error_help method via module pattern matching"""
        analyzer = SimpleErrorAnalyzer()
        
        # Create a mock MySQL error
        class MockMySQLError(Exception):
            pass
        
        # Set the module to match pattern
        MockMySQLError.__module__ = "mysql.connector.errors"
        
        error = MockMySQLError("MySQL connection failed")
        context = {"operation": "mysql_insert"}
        
        result = analyzer.analyze_error(error, context)
        
        assert result is not None
        assert "MySQL Error" in result
        assert "credentials" in result
    
    def test_elasticsearch_error_help(self):
        """Test _elasticsearch_error_help method via module pattern matching"""
        analyzer = SimpleErrorAnalyzer()
        
        # Create a mock Elasticsearch error
        class MockESError(Exception):
            pass
        
        # Set the module to match pattern
        MockESError.__module__ = "elasticsearch.exceptions"
        
        error = MockESError("ES connection failed")
        context = {"operation": "es_query"}
        
        result = analyzer.analyze_error(error, context)
        
        assert result is not None
        assert "Elasticsearch Error" in result
        assert "Elasticsearch is running" in result
    
    def test_generic_help_fallback(self):
        """Test _generic_help for unknown error types"""
        analyzer = SimpleErrorAnalyzer()
        
        # Create a custom error that won't match any pattern
        class CustomUnknownError(Exception):
            pass
        
        error = CustomUnknownError("Unknown error")
        context = {"operation": "unknown_op"}
        
        result = analyzer.analyze_error(error, context)
        
        assert result is not None
        assert "CustomUnknownError" in result
        assert "error message" in result
        assert "configuration" in result
    
    def test_connection_refused_with_context(self):
        """Test connection refused includes operation in output"""
        analyzer = SimpleErrorAnalyzer()
        error = ConnectionRefusedError("Connection refused")
        context = {"operation": "database_connect", "host": "localhost"}
        
        result = analyzer.analyze_error(error, context)
        
        assert "database_connect" in result
        assert "Connection Refused" in result


class TestClaudeErrorAnalyzerInitialization:
    """Test ClaudeErrorAnalyzer initialization scenarios"""
    
    def test_init_with_explicit_api_key(self):
        """Test initialization with explicit API key"""
        analyzer = ClaudeErrorAnalyzer(api_key="explicit-key")
        
        assert analyzer.api_key == "explicit-key"
        assert analyzer.is_enabled() is True
    
    def test_init_with_env_api_key(self):
        """Test initialization reading from environment"""
        with patch.dict(os.environ, {'ANTHROPIC_API_KEY': 'env-key'}):
            analyzer = ClaudeErrorAnalyzer()
            
            assert analyzer.api_key == "env-key"
            assert analyzer.is_enabled() is True
    
    def test_init_without_api_key(self):
        """Test initialization without API key"""
        with patch.dict(os.environ, {}, clear=True):
            analyzer = ClaudeErrorAnalyzer()
            
            assert analyzer.api_key is None
            assert analyzer.is_enabled() is False
    
    def test_init_custom_model(self):
        """Test initialization with custom model"""
        analyzer = ClaudeErrorAnalyzer(api_key="test-key", model="claude-opus-4")
        
        assert analyzer.model == "claude-opus-4"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
