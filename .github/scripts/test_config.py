"""
Test configuration helper for database connections.
Reads connection parameters from environment variables with sensible defaults.
"""
import os


def get_mysql_config():
    """
    Get MySQL configuration from environment variables.
    
    Returns:
        dict: MySQL connection parameters for testing
    """
    return {
        'host': os.getenv('MYSQL_HOST', 'localhost'),
        'port': int(os.getenv('MYSQL_PORT', '3306')),
        'user': os.getenv('MYSQL_USER', 'root'),
        'password': os.getenv('MYSQL_PASSWORD', 'testpassword'),
        'database': os.getenv('MYSQL_DATABASE', 'testdb'),
    }


def get_elasticsearch_config():
    """
    Get Elasticsearch configuration from environment variables.
    
    Returns:
        dict: Elasticsearch connection parameters for testing
    """
    return {
        'url': os.getenv('ELASTICSEARCH_URL', 'http://localhost:9200'),
        'username': os.getenv('ELASTICSEARCH_USER'),
        'password': os.getenv('ELASTICSEARCH_PASSWORD'),
        'api_key': os.getenv('ELASTICSEARCH_API_KEY'),
    }


# For backward compatibility
MYSQL_TEST_CONFIG = get_mysql_config()
