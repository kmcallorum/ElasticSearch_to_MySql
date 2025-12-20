"""
Error analysis system with AI-powered troubleshooting suggestions

Author: Mac McAllorum (kevin_mcallorum@linux.com)
GitHub: github.com/kmcallorum
License: MIT
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
import logging
import json
import os
import traceback

logger = logging.getLogger(__name__)


class ErrorAnalyzer(ABC):
    """Abstract base class for error analysis"""
    
    @abstractmethod
    def analyze_error(self, error: Exception, context: Dict[str, Any]) -> Optional[str]:
        """
        Analyze an error and provide troubleshooting suggestions.
        
        Args:
            error: The exception that was raised
            context: Dictionary with context about where/when error occurred
                    e.g., {"operation": "mysql_insert", "record_id": "123", "attempt": 1}
        
        Returns:
            String with troubleshooting suggestions, or None if no analysis available
        """
        pass
    
    @abstractmethod
    def is_enabled(self) -> bool:
        """Check if error analysis is enabled"""
        pass


class NoOpErrorAnalyzer(ErrorAnalyzer):
    """Default error analyzer that does nothing - for when AI is disabled"""
    
    def analyze_error(self, error: Exception, context: Dict[str, Any]) -> Optional[str]:
        """No analysis provided"""
        return None
    
    def is_enabled(self) -> bool:
        """AI analysis is disabled"""
        return False


class ClaudeErrorAnalyzer(ErrorAnalyzer):
    """
    AI-powered error analyzer using Claude API
    
    Provides context-aware troubleshooting suggestions for data pipeline errors.
    """
    
    def __init__(self, api_key: Optional[str] = None, model: str = "claude-sonnet-4-20250514"):
        """
        Initialize Claude error analyzer.
        
        Args:
            api_key: Anthropic API key (or reads from ANTHROPIC_API_KEY env var)
            model: Claude model to use for analysis
        """
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        self.model = model
        
        if not self.api_key:
            logger.warning("No API key provided for AI error analysis. Set ANTHROPIC_API_KEY environment variable.")
            self._enabled = False
        else:
            self._enabled = True
            logger.info("AI-powered error analysis enabled")
    
    def is_enabled(self) -> bool:
        """Check if analyzer has valid API key"""
        return self._enabled
    
    def analyze_error(self, error: Exception, context: Dict[str, Any]) -> Optional[str]:
        """
        Use Claude to analyze error and provide suggestions.
        
        Args:
            error: The exception that occurred
            context: Context about the error (operation, record_id, etc.)
        
        Returns:
            Formatted troubleshooting suggestions
        """
        if not self.is_enabled():
            return None
        
        try:
            # Build error context
            error_type = type(error).__name__
            error_message = str(error)
            error_traceback = traceback.format_exc()
            
            # Create prompt for Claude
            prompt = self._build_prompt(error_type, error_message, error_traceback, context)
            
            # Call Claude API
            suggestions = self._call_claude_api(prompt)
            
            return suggestions
            
        except Exception as e:
            logger.error(f"Error during AI analysis (non-critical): {e}")
            return None
    
    def _build_prompt(self, error_type: str, error_message: str, 
                     error_traceback: str, context: Dict[str, Any]) -> str:
        """Build the prompt for Claude"""
        
        prompt = f"""You are helping troubleshoot a data pipeline error. Provide concise, actionable troubleshooting steps.

ERROR DETAILS:
Type: {error_type}
Message: {error_message}

CONTEXT:
{json.dumps(context, indent=2)}

STACK TRACE:
{error_traceback}

Provide 3-5 specific troubleshooting steps, prioritized by likelihood. Be concise and actionable.
Focus on the most common causes for this type of error in data pipelines.

Format your response as:
🤖 AI Troubleshooting Suggestions:

1. [Most likely cause and how to fix]
2. [Second most likely cause and how to fix]
3. [Additional steps if needed]

Keep each step under 2 sentences. Be specific to the error context."""
        
        return prompt
    
    def _call_claude_api(self, prompt: str) -> str:
        """
        Make API call to Claude.
        
        Args:
            prompt: The analysis prompt
            
        Returns:
            Claude's response with suggestions
        """
        try:
            import anthropic
            
            client = anthropic.Anthropic(api_key=self.api_key)
            
            message = client.messages.create(
                model=self.model,
                max_tokens=1000,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )
            
            # Extract text from response
            response_text = message.content[0].text
            return response_text
            
        except ImportError:
            logger.error("anthropic package not installed. Install with: pip install anthropic")
            return "❌ Cannot analyze error: 'anthropic' package not installed"
        except Exception as e:
            logger.error(f"Claude API call failed: {e}")
            return f"❌ AI analysis failed: {str(e)}"


class SimpleErrorAnalyzer(ErrorAnalyzer):
    """
    Simple rule-based error analyzer (no API required).
    
    Provides basic troubleshooting for common errors without AI.
    Good fallback when API key is not available.
    """
    
    def __init__(self):
        self.error_patterns = {
            "ConnectionRefusedError": self._connection_refused_help,
            "TimeoutError": self._timeout_help,
            "PermissionError": self._permission_help,
            "FileNotFoundError": self._file_not_found_help,
            "JSONDecodeError": self._json_decode_help,
            "KeyError": self._key_error_help,
            "mysql.connector.errors": self._mysql_error_help,
            "elasticsearch.exceptions": self._elasticsearch_error_help,
        }
    
    def is_enabled(self) -> bool:
        return True
    
    def analyze_error(self, error: Exception, context: Dict[str, Any]) -> Optional[str]:
        """Provide rule-based error suggestions"""
        error_type = type(error).__name__
        error_module = type(error).__module__
        
        # Check for specific error type
        if error_type in self.error_patterns:
            return self.error_patterns[error_type](error, context)
        
        # Check for module-level patterns
        for pattern, handler in self.error_patterns.items():
            if pattern in error_module:
                return handler(error, context)
        
        # Generic fallback
        return self._generic_help(error, context)
    
    def _connection_refused_help(self, error: Exception, context: Dict[str, Any]) -> str:
        operation = context.get("operation", "unknown")
        return f"""
💡 Troubleshooting: Connection Refused

1. Check if the service is running (MySQL, Elasticsearch, etc.)
2. Verify the host and port are correct
3. Check firewall rules - may be blocking the connection
4. If using 'localhost', try '127.0.0.1' or vice versa

Operation: {operation}
"""
    
    def _timeout_help(self, error: Exception, context: Dict[str, Any]) -> str:
        return """
💡 Troubleshooting: Timeout

1. Check network connectivity to the service
2. Service may be overloaded - check system resources
3. Increase timeout value in configuration
4. Check for slow queries or operations
"""
    
    def _permission_help(self, error: Exception, context: Dict[str, Any]) -> str:
        return """
💡 Troubleshooting: Permission Denied

1. Check file/directory permissions: ls -la
2. Verify user has necessary database privileges
3. Check if running with correct user account
4. For files: chmod/chown to fix permissions
"""
    
    def _file_not_found_help(self, error: Exception, context: Dict[str, Any]) -> str:
        return """
💡 Troubleshooting: File Not Found

1. Verify the file path is correct (absolute vs relative)
2. Check if file exists: ls -la <filepath>
3. Verify working directory is correct: pwd
4. Check for typos in filename
"""
    
    def _json_decode_help(self, error: Exception, context: Dict[str, Any]) -> str:
        return """
💡 Troubleshooting: JSON Decode Error

1. Check if content is valid JSON - might be HTML error page
2. Verify API is returning expected format
3. Check for empty responses
4. Use json.loads() to see exact parsing error
"""
    
    def _key_error_help(self, error: Exception, context: Dict[str, Any]) -> str:
        missing_key = str(error).strip("'")
        return f"""
💡 Troubleshooting: Missing Key '{missing_key}'

1. Check if data structure matches expected format
2. Verify CSV column names match configuration
3. Data source may have changed schema
4. Use .get() with defaults for optional fields
"""
    
    def _mysql_error_help(self, error: Exception, context: Dict[str, Any]) -> str:
        return """
💡 Troubleshooting: MySQL Error

1. Verify credentials (username, password, database name)
2. Check if MySQL service is running
3. Verify host and port (default: localhost:3306)
4. Check user privileges: GRANT ALL ON database.*
"""
    
    def _elasticsearch_error_help(self, error: Exception, context: Dict[str, Any]) -> str:
        return """
💡 Troubleshooting: Elasticsearch Error

1. Verify Elasticsearch is running: curl localhost:9200
2. Check authentication credentials
3. Verify index name exists
4. Check Elasticsearch logs for detailed errors
"""
    
    def _generic_help(self, error: Exception, context: Dict[str, Any]) -> str:
        return f"""
💡 Troubleshooting: {type(error).__name__}

1. Check the error message above for specific details
2. Review configuration settings
3. Check logs for additional context: pipeline.log
4. Verify all required services are running
"""
