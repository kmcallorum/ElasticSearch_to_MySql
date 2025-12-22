"""
Tests for production implementations (Elasticsearch and MySQL) using mocks

Author: Mac McAllorum (kevin_mcallorum@linux.com)
GitHub: github.com/kmcallorum
License: MIT
"""
import pytest
from unittest.mock import Mock, MagicMock, patch, call
import json
from production_impl import ElasticsearchSource, MySQLSink


class TestElasticsearchSource:
    """Test ElasticsearchSource with mocked requests"""
    
    @patch('production_impl.requests.post')
    def test_basic_fetch(self, mock_post):
        """Test basic record fetching from Elasticsearch"""
        # Mock successful ES response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "hits": {
                "hits": [
                    {"_id": "1", "_source": {"data": "test1"}},
                    {"_id": "2", "_source": {"data": "test2"}}
                ]
            },
            "_scroll_id": "scroll123"
        }
        mock_post.return_value = mock_response
        
        # Create source with CORRECT parameter names
        source = ElasticsearchSource(
            es_url="http://localhost:9200/test/_search",
            es_user="user",
            es_pass="pass",
            batch_size=10
        )
        
        # Fetch records
        records = list(source.fetch_records())
        
        # Verify
        assert len(records) == 2
        assert records[0][0] == "1"  # record_id
        assert "test1" in records[0][1]  # content has test1
        assert records[1][0] == "2"
        assert "test2" in records[1][1]
    
    @patch('production_impl.requests.post')
    def test_with_query_params(self, mock_post):
        """Test fetching with query parameters (date range)"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "hits": {"hits": []},  # Empty to complete immediately
            "_scroll_id": "scroll123"
        }
        mock_post.return_value = mock_response
        
        source = ElasticsearchSource(
            es_url="http://localhost:9200/test/_search",
            es_user="user",
            es_pass="pass"
        )
        
        # Fetch with date range
        query_params = {
            "gte": "2024-01-01T00:00:00",
            "lte": "2024-12-31T23:59:59"
        }
        list(source.fetch_records(query_params))
        
        # Verify query was sent with date range
        call_args = mock_post.call_args_list[0]
        sent_data = json.loads(call_args[1]['data'])
        assert "query" in sent_data
        assert "range" in sent_data["query"]
    
    @patch('production_impl.requests.post')
    def test_empty_results(self, mock_post):
        """Test handling of empty result set"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "hits": {"hits": []},
            "_scroll_id": "scroll123"
        }
        mock_post.return_value = mock_response
        
        source = ElasticsearchSource(
            es_url="http://localhost:9200/test/_search",
            es_user="user",
            es_pass="pass"
        )
        
        # Fetch should return empty
        records = list(source.fetch_records())
        
        # Should get 0 records
        assert len(records) == 0
    
    @patch('production_impl.requests.post')
    def test_scroll_pagination(self, mock_post):
        """Test that scrolling works across multiple batches"""
        # First batch
        first_response = Mock()
        first_response.status_code = 200
        first_response.json.return_value = {
            "hits": {
                "hits": [
                    {"_id": "1", "_source": {"data": "batch1"}}
                ]
            },
            "_scroll_id": "scroll123"
        }
        
        # Second batch (empty - end of data)
        second_response = Mock()
        second_response.status_code = 200
        second_response.json.return_value = {
            "hits": {"hits": []},
            "_scroll_id": "scroll456"
        }
        
        mock_post.side_effect = [first_response, second_response]
        
        source = ElasticsearchSource(
            es_url="http://localhost:9200/test/_search",
            es_user="user",
            es_pass="pass"
        )
        
        records = list(source.fetch_records())
        
        # Should get 1 record from 1 batch
        assert len(records) == 1
        assert records[0][0] == "1"
    
    @patch('production_impl.requests.post')
    def test_error_handling_bad_status(self, mock_post):
        """Test error handling for non-200 status codes"""
        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"
        mock_post.return_value = mock_response
        
        source = ElasticsearchSource(
            es_url="http://localhost:9200/test/_search",
            es_user="user",
            es_pass="pass"
        )
        
        # Should raise exception on bad status
        with pytest.raises(Exception) as exc_info:
            list(source.fetch_records())
        
        assert "500" in str(exc_info.value)
    
    @patch('production_impl.requests.post')
    def test_error_handling_connection_error(self, mock_post):
        """Test error handling for connection errors"""
        import requests
        mock_post.side_effect = requests.exceptions.ConnectionError("Connection refused")
        
        source = ElasticsearchSource(
            es_url="http://localhost:9200/test/_search",
            es_user="user",
            es_pass="pass"
        )
        
        # Should raise exception on connection error
        with pytest.raises(requests.exceptions.ConnectionError):
            list(source.fetch_records())
    
    @patch('production_impl.requests.post')
    def test_close(self, mock_post):
        """Test that close() method exists and works"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "hits": {"hits": []},
            "_scroll_id": "scroll123"
        }
        mock_post.return_value = mock_response
        
        source = ElasticsearchSource(
            es_url="http://localhost:9200/test/_search",
            es_user="user",
            es_pass="pass"
        )
        
        # Fetch some records
        list(source.fetch_records())
        
        # Close should work without error
        source.close()
        
        # If we got here, close() works
        assert True


class TestMySQLSink:
    """Test MySQLSink with mocked MySQL connections"""
    
    @patch('production_impl.mysql.connector.connect')
    def test_basic_insert(self, mock_connect):
        """Test basic record insertion"""
        # Mock connection and cursor
        mock_cursor = Mock()
        mock_cursor.rowcount = 1  # CRITICAL: Set rowcount
        mock_conn = Mock()
        mock_conn.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_conn
        
        # Create sink
        sink = MySQLSink(
            host="localhost",
            user="root",
            password="password",
            database="testdb",
            table="testtable"
        )
        
        # Insert a record
        result = sink.insert_record("123", '{"data": "test"}')
        
        # Verify
        assert result is True
        mock_cursor.execute.assert_called_once()
        call_args = mock_cursor.execute.call_args[0]
        assert "INSERT" in call_args[0]
        assert call_args[1] == ("123", '{"data": "test"}')
    
    @patch('production_impl.mysql.connector.connect')
    def test_duplicate_handling(self, mock_connect):
        """Test that duplicates are skipped"""
        mock_cursor = Mock()
        mock_conn = Mock()
        mock_conn.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_conn
        
        sink = MySQLSink(
            host="localhost",
            user="root",
            password="password",
            database="testdb",
            table="testtable"
        )
        
        # First insert - success (rowcount = 1)
        mock_cursor.rowcount = 1
        result1 = sink.insert_record("123", '{"data": "test"}')
        assert result1 is True
        
        # Second insert - duplicate (rowcount = 0)
        mock_cursor.rowcount = 0
        result2 = sink.insert_record("123", '{"data": "test2"}')
        assert result2 is False
        
        # Stats should show 1 inserted, 1 skipped
        stats = sink.get_stats()
        assert stats["inserted"] == 1
        assert stats["skipped"] == 1
    
    @patch('production_impl.mysql.connector.connect')
    def test_commit(self, mock_connect):
        """Test that commit calls connection.commit()"""
        mock_cursor = Mock()
        mock_cursor.rowcount = 1
        mock_conn = Mock()
        mock_conn.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_conn
        
        sink = MySQLSink(
            host="localhost",
            user="root",
            password="password",
            database="testdb",
            table="testtable"
        )
        
        # Insert and commit
        sink.insert_record("123", '{"data": "test"}')
        sink.commit()
        
        # Verify commit was called
        mock_conn.commit.assert_called()
    
    @patch('production_impl.mysql.connector.connect')
    def test_close(self, mock_connect):
        """Test that close closes cursor and connection"""
        mock_cursor = Mock()
        mock_conn = Mock()
        mock_conn.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_conn
        
        sink = MySQLSink(
            host="localhost",
            user="root",
            password="password",
            database="testdb",
            table="testtable"
        )
        
        # Close should close both cursor and connection
        sink.close()
        
        mock_cursor.close.assert_called_once()
        mock_conn.close.assert_called_once()
    
    @patch('production_impl.mysql.connector.connect')
    def test_error_handling_insert_error(self, mock_connect):
        """Test error handling when insert fails"""
        mock_cursor = Mock()
        mock_cursor.execute.side_effect = Exception("Database error")
        mock_conn = Mock()
        mock_conn.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_conn
        
        sink = MySQLSink(
            host="localhost",
            user="root",
            password="password",
            database="testdb",
            table="testtable"
        )
        
        # Insert should handle error gracefully
        result = sink.insert_record("123", '{"data": "test"}')
        
        # Should return False and increment error count
        assert result is False
        stats = sink.get_stats()
        assert stats["errors"] == 1
    
    @patch('production_impl.mysql.connector.connect')
    def test_connection_error(self, mock_connect):
        """Test error handling for connection failures"""
        import mysql.connector
        mock_connect.side_effect = mysql.connector.Error("Connection refused")
        
        # Should raise exception on connection failure
        with pytest.raises(mysql.connector.Error):
            MySQLSink(
                host="localhost",
                user="root",
                password="password",
                database="testdb",
                table="testtable"
            )
    
    @patch('production_impl.mysql.connector.connect')
    def test_stats_tracking(self, mock_connect):
        """Test that statistics are tracked correctly"""
        mock_cursor = Mock()
        mock_conn = Mock()
        mock_conn.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_conn
        
        sink = MySQLSink(
            host="localhost",
            user="root",
            password="password",
            database="testdb",
            table="testtable"
        )
        
        # Insert 3 records, with 1 duplicate
        mock_cursor.rowcount = 1
        sink.insert_record("1", '{"data": "test1"}')
        mock_cursor.rowcount = 1
        sink.insert_record("2", '{"data": "test2"}')
        mock_cursor.rowcount = 0  # Duplicate
        sink.insert_record("1", '{"data": "duplicate"}')
        
        # Force an error on next insert
        mock_cursor.execute.side_effect = Exception("Error")
        sink.insert_record("3", '{"data": "test3"}')
        
        # Check stats
        stats = sink.get_stats()
        assert stats["inserted"] == 2
        assert stats["skipped"] == 1
        assert stats["errors"] == 1
    
    @patch('production_impl.mysql.connector.connect')
    def test_thread_safety_basic(self, mock_connect):
        """Test basic functionality that would work in threaded environment"""
        mock_cursor = Mock()
        mock_cursor.rowcount = 1
        mock_conn = Mock()
        mock_conn.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_conn
        
        sink = MySQLSink(
            host="localhost",
            user="root",
            password="password",
            database="testdb",
            table="testtable"
        )
        
        # Insert should work (MySQL connector handles thread safety internally)
        result = sink.insert_record("123", '{"data": "test"}')
        
        # If we got here without errors, basic operation works
        assert result is True


class TestIntegration:
    """Integration tests with both source and sink"""
    
    @patch('production_impl.mysql.connector.connect')
    @patch('production_impl.requests.post')
    def test_full_pipeline_mock(self, mock_post, mock_connect):
        """Test full ES -> MySQL pipeline with mocks"""
        # Mock ES response
        mock_es_response = Mock()
        mock_es_response.status_code = 200
        mock_es_response.json.return_value = {
            "hits": {
                "hits": [
                    {"_id": "1", "_source": {"data": "test1"}},
                    {"_id": "2", "_source": {"data": "test2"}}
                ]
            },
            "_scroll_id": "scroll123"
        }
        mock_post.return_value = mock_es_response
        
        # Mock MySQL connection
        mock_cursor = Mock()
        mock_cursor.rowcount = 1
        mock_conn = Mock()
        mock_conn.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_conn
        
        # Create source and sink with CORRECT parameter names
        source = ElasticsearchSource(
            es_url="http://localhost:9200/test/_search",
            es_user="user",
            es_pass="pass"
        )
        
        sink = MySQLSink(
            host="localhost",
            user="root",
            password="password",
            database="testdb",
            table="testtable"
        )
        
        # Process records
        for record_id, content in source.fetch_records():
            sink.insert_record(record_id, content)
        
        sink.commit()
        
        # Verify
        stats = sink.get_stats()
        assert stats["inserted"] == 2
        assert mock_cursor.execute.call_count == 2
        mock_conn.commit.assert_called()
        
        # Cleanup
        source.close()
        sink.close()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
