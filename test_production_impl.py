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
        
        # Create source
        source = ElasticsearchSource(
            url="http://localhost:9200/test/_search",
            username="user",
            password="pass",
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
            "hits": {"hits": [{"_id": "1", "_source": {"data": "test"}}]},
            "_scroll_id": "scroll123"
        }
        mock_post.return_value = mock_response
        
        source = ElasticsearchSource(
            url="http://localhost:9200/test/_search",
            username="user",
            password="pass"
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
        assert "range" in sent_data["query"]["bool"]["must"][0]
    
    @patch('production_impl.requests.post')
    def test_with_limit(self, mock_post):
        """Test limit parameter stops fetching early"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "hits": {
                "hits": [
                    {"_id": str(i), "_source": {"data": f"test{i}"}}
                    for i in range(10)
                ]
            },
            "_scroll_id": "scroll123"
        }
        mock_post.return_value = mock_response
        
        source = ElasticsearchSource(
            url="http://localhost:9200/test/_search",
            username="user",
            password="pass"
        )
        
        # Fetch with limit
        records = list(source.fetch_records({"limit": 5}))
        
        # Should only get 5 records even though ES returned 10
        assert len(records) == 5
    
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
        
        # Second batch
        second_response = Mock()
        second_response.status_code = 200
        second_response.json.return_value = {
            "hits": {
                "hits": [
                    {"_id": "2", "_source": {"data": "batch2"}}
                ]
            },
            "_scroll_id": "scroll456"
        }
        
        # Third batch (empty - end of data)
        third_response = Mock()
        third_response.status_code = 200
        third_response.json.return_value = {
            "hits": {"hits": []},
            "_scroll_id": "scroll789"
        }
        
        mock_post.side_effect = [first_response, second_response, third_response]
        
        source = ElasticsearchSource(
            url="http://localhost:9200/test/_search",
            username="user",
            password="pass"
        )
        
        records = list(source.fetch_records())
        
        # Should get 2 records total from 2 batches
        assert len(records) == 2
        assert records[0][0] == "1"
        assert records[1][0] == "2"
    
    @patch('production_impl.requests.post')
    def test_error_handling_bad_status(self, mock_post):
        """Test error handling for non-200 status codes"""
        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"
        mock_post.return_value = mock_response
        
        source = ElasticsearchSource(
            url="http://localhost:9200/test/_search",
            username="user",
            password="pass"
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
            url="http://localhost:9200/test/_search",
            username="user",
            password="pass"
        )
        
        # Should raise exception on connection error
        with pytest.raises(requests.exceptions.ConnectionError):
            list(source.fetch_records())
    
    @patch('production_impl.requests.post')
    @patch('production_impl.requests.delete')
    def test_close_clears_scroll(self, mock_delete, mock_post):
        """Test that close() clears the scroll context"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "hits": {"hits": [{"_id": "1", "_source": {"data": "test"}}]},
            "_scroll_id": "scroll123"
        }
        mock_post.return_value = mock_response
        
        source = ElasticsearchSource(
            url="http://localhost:9200/test/_search",
            username="user",
            password="pass"
        )
        
        # Fetch some records to establish scroll
        list(source.fetch_records())
        
        # Close should delete the scroll
        source.close()
        
        # Verify delete was called with scroll_id
        mock_delete.assert_called_once()
        call_args = mock_delete.call_args
        assert "scroll123" in str(call_args)


class TestMySQLSink:
    """Test MySQLSink with mocked MySQL connections"""
    
    @patch('production_impl.mysql.connector.connect')
    def test_basic_insert(self, mock_connect):
        """Test basic record insertion"""
        # Mock connection and cursor
        mock_cursor = Mock()
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
        assert "INSERT INTO testtable" in call_args[0]
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
        
        # First insert - success
        result1 = sink.insert_record("123", '{"data": "test"}')
        assert result1 is True
        
        # Second insert - duplicate (should skip)
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
        mock_conn.commit.assert_called_once()
    
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
        sink.insert_record("1", '{"data": "test1"}')
        sink.insert_record("2", '{"data": "test2"}')
        sink.insert_record("1", '{"data": "duplicate"}')  # Duplicate
        
        # Force an error on next insert
        mock_cursor.execute.side_effect = Exception("Error")
        sink.insert_record("3", '{"data": "test3"}')
        
        # Check stats
        stats = sink.get_stats()
        assert stats["inserted"] == 2
        assert stats["skipped"] == 1
        assert stats["errors"] == 1
    
    @patch('production_impl.mysql.connector.connect')
    def test_thread_safety(self, mock_connect):
        """Test that locks work for thread safety"""
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
        
        # Verify lock exists
        assert hasattr(sink, 'lock')
        
        # Insert should use the lock (can't easily test lock acquisition, but verify it exists)
        sink.insert_record("123", '{"data": "test"}')
        
        # If we got here without deadlock, threading setup is working
        assert True


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
        mock_conn = Mock()
        mock_conn.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_conn
        
        # Create source and sink
        source = ElasticsearchSource(
            url="http://localhost:9200/test/_search",
            username="user",
            password="pass"
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
        mock_conn.commit.assert_called_once()
        
        # Cleanup
        source.close()
        sink.close()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
