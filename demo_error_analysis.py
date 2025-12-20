#!/usr/bin/env python3
"""
Demo script showing AI-powered error analysis in action

This script intentionally creates various errors to demonstrate
how the AI error analyzer provides helpful troubleshooting suggestions.

Author: Mac McAllorum (kevin_mcallorum@linux.com)
"""
import sys
import logging
from error_analyzer import ClaudeErrorAnalyzer, SimpleErrorAnalyzer

# Setup logging to see the suggestions
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)


def demo_connection_error():
    """Simulate a database connection error"""
    print("\n" + "="*60)
    print("DEMO 1: Connection Refused Error")
    print("="*60)
    
    error = ConnectionRefusedError("Connection refused on localhost:3306")
    context = {
        "operation": "mysql_connect",
        "host": "localhost",
        "port": 3306,
        "user": "root"
    }
    
    # Show with simple analyzer
    print("\n--- Simple Rule-Based Analysis ---")
    simple = SimpleErrorAnalyzer()
    suggestion = simple.analyze_error(error, context)
    print(suggestion)
    
    # Show with AI analyzer (if API key available)
    print("\n--- AI-Powered Analysis ---")
    ai = ClaudeErrorAnalyzer()
    if ai.is_enabled():
        suggestion = ai.analyze_error(error, context)
        print(suggestion)
    else:
        print("❌ AI analysis not available (set ANTHROPIC_API_KEY)")


def demo_timeout_error():
    """Simulate a timeout error"""
    print("\n" + "="*60)
    print("DEMO 2: Timeout Error")
    print("="*60)
    
    error = TimeoutError("Operation timed out after 30 seconds")
    context = {
        "operation": "elasticsearch_scroll",
        "index": "large_index",
        "batch_size": 10000,
        "elapsed": 30.0
    }
    
    print("\n--- Simple Analysis ---")
    simple = SimpleErrorAnalyzer()
    suggestion = simple.analyze_error(error, context)
    print(suggestion)


def demo_permission_error():
    """Simulate a permission error"""
    print("\n" + "="*60)
    print("DEMO 3: Permission Denied Error")
    print("="*60)
    
    error = PermissionError("Permission denied: '/var/log/output.jsonl'")
    context = {
        "operation": "file_write",
        "filepath": "/var/log/output.jsonl",
        "user": "datauser"
    }
    
    print("\n--- Simple Analysis ---")
    simple = SimpleErrorAnalyzer()
    suggestion = simple.analyze_error(error, context)
    print(suggestion)


def demo_json_error():
    """Simulate a JSON parsing error"""
    print("\n" + "="*60)
    print("DEMO 4: JSON Decode Error")
    print("="*60)
    
    import json
    try:
        json.loads("{'invalid': json}")
    except json.JSONDecodeError as error:
        context = {
            "operation": "elasticsearch_response_parse",
            "url": "http://localhost:9200/index/_search",
            "response_preview": "<!DOCTYPE html><html><head><title>Error</title>"
        }
        
        print("\n--- Simple Analysis ---")
        simple = SimpleErrorAnalyzer()
        suggestion = simple.analyze_error(error, context)
        print(suggestion)


def demo_key_error():
    """Simulate a missing key error"""
    print("\n" + "="*60)
    print("DEMO 5: Missing CSV Column Error")
    print("="*60)
    
    error = KeyError("customer_id")
    context = {
        "operation": "csv_parse",
        "filepath": "data.csv",
        "expected_columns": ["customer_id", "name", "email"],
        "actual_columns": ["id", "name", "email"]
    }
    
    print("\n--- Simple Analysis ---")
    simple = SimpleErrorAnalyzer()
    suggestion = simple.analyze_error(error, context)
    print(suggestion)


def main():
    """Run all demos"""
    print("\n")
    print("╔" + "="*58 + "╗")
    print("║" + " "*58 + "║")
    print("║" + "  AI-Powered Error Analysis - Demo".center(58) + "║")
    print("║" + " "*58 + "║")
    print("╚" + "="*58 + "╝")
    
    # Check if AI is available
    ai = ClaudeErrorAnalyzer()
    if ai.is_enabled():
        print("\n✅ AI-powered analysis is ENABLED")
        print("   Using Anthropic API for intelligent suggestions")
    else:
        print("\n⚠️  AI-powered analysis is DISABLED")
        print("   Set ANTHROPIC_API_KEY environment variable to enable")
        print("   Showing rule-based analysis only")
    
    # Run demos
    demo_connection_error()
    demo_timeout_error()
    demo_permission_error()
    demo_json_error()
    demo_key_error()
    
    print("\n" + "="*60)
    print("Demo complete!")
    print("="*60)
    
    print("\n💡 Tips:")
    print("  - Use --simple-errors for rule-based analysis (no API required)")
    print("  - Use --ai-errors for AI-powered analysis (requires API key)")
    print("  - Default: no error analysis (fastest)")
    
    print("\n📚 Example usage:")
    print("  python pipeline_cli.py --source_type csv --sink_type file \\")
    print("    --csv_file data.csv --output_file output.jsonl \\")
    print("    --ai-errors  # Enable AI analysis")


if __name__ == "__main__":
    main()
