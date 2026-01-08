"""
Comprehensive edge case tests for production_impl.py to reach 100% coverage

These tests target uncovered lines:
- Lines 34, 38: Authentication edge cases
- Lines 84-85: Query building edge cases  
- Line 102: Error handling in scroll

Author: Kevin McAllorum (kevin_mcallorum@linux.com)
"""
import pytest
from unittest.mock import Mock, patch
import json
from production_impl import ElasticsearchSource, MySQLSink


class TestElasticsearchSourceEdgeCases:
    """Test edge cases in ElasticsearchSource"""
    
    def test_authentication_with_api_key(self):
        """Test ES source with API key authentication"""
        source = ElasticsearchSource(
            es_url="http://localhost:9200/test/_search",
            api_key="test-api-key-12345",
            batch_size=100
        )
        
        # Verify API key is in headers
        assert "Authorization" in source.headers
        assert source.headers["Authorization"] == "ApiKey test-api-key-12345"
        assert source.auth is None
    
    def test_authentication_with_user_pass(self):
        """Test ES source with username/password authentication"""
        source = ElasticsearchSource(
            es_url="http://localhost:9200/test/_search",
            es_user="admin",
            es_pass="secret",
            batch_size=100
        )
        
        # Verify basic auth is set
        assert source.auth == ("admin", "secret")
        assert "Authorization" not in source.headers
    
    def test_authentication_missing_both(self):
        """Test ES source with no authentication raises error"""
        with pytest.raises(ValueError) as exc_info:
            ElasticsearchSource(
                es_url="http://localhost:9200/test/_search",
                batch_size=100
            )
        
        assert "api_key or both es_user and es_pass must be provided" in str(exc_info.value)
    
    def test_authentication_missing_password(self):
        """Test ES source with only username raises error"""
        with pytest.raises(ValueError) as exc_info:
            ElasticsearchSource(
                es_url="http://localhost:9200/test/_search",
                es_user="admin",
                batch_size=100
            )
        
        assert "api_key or both es_user and es_pass must be provided" in str(exc_info.value)
    
    @patch('production_impl.requests.post')
    def test_query_building_match_all(self, mock_post):
        """Test query building with match_all"""
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
        
        # Query with match_all
        list(source.fetch_records({"match_all": True}))
        
        # Verify the query sent
        call_args = mock_post.call_args_list[0]
        sent_query = json.loads(call_args[1]['data'])
        
        assert sent_query == {"query": {"match_all": {}}}
    
    @patch('production_impl.requests.post')
    def test_query_building_with_date_range(self, mock_post):
        """Test query building with date range"""
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
        
        # Query with date range
        query_params = {
            "gte": "2024-01-01T00:00:00",
            "lte": "2024-12-31T23:59:59"
        }
        list(source.fetch_records(query_params))
        
        # Verify the query sent
        call_args = mock_post.call_args_list[0]
        sent_query = json.loads(call_args[1]['data'])
        
        assert "query" in sent_query
        assert "range" in sent_query["query"]
        assert "@timestamp" in sent_query["query"]["range"]
        assert sent_query["query"]["range"]["@timestamp"]["gte"] == "2024-01-01T00:00:00"
        assert sent_query["query"]["range"]["@timestamp"]["lte"] == "2024-12-31T23:59:59"
    
    def test_query_building_missing_gte(self):
        """Test query building with missing gte raises error"""
        source = ElasticsearchSource(
            es_url="http://localhost:9200/test/_search",
            es_user="user",
            es_pass="pass"
        )
        
        with pytest.raises(ValueError) as exc_info:
            list(source.fetch_records({"lte": "2024-12-31T23:59:59"}))
        
        assert "gte and lte required" in str(exc_info.value)
    
    def test_query_building_missing_lte(self):
        """Test query building with missing lte raises error"""
        source = ElasticsearchSource(
            es_url="http://localhost:9200/test/_search",
            es_user="user",
            es_pass="pass"
        )
        
        with pytest.raises(ValueError) as exc_info:
            list(source.fetch_records({"gte": "2024-01-01T00:00:00"}))
        
        assert "gte and lte required" in str(exc_info.value)
    
    @patch('production_impl.requests.post')
    def test_scroll_error_handling(self, mock_post):
        """Test error handling during scroll"""
        # First request succeeds
        first_response = Mock()
        first_response.status_code = 200
        first_response.json.return_value = {
            "hits": {"hits": [
                {"_id": "1", "_source": {"data": "test1"}}
            ]},
            "_scroll_id": "scroll123"
        }
        
        # Second request fails
        error_response = Mock()
        error_response.status_code = 500
        error_response.text = "Internal Server Error"
        
        mock_post.side_effect = [first_response, error_response]
        
        source = ElasticsearchSource(
            es_url="http://localhost:9200/test/_search",
            es_user="user",
            es_pass="pass"
        )
        
        # Should get one record then stop due to error
        records = list(source.fetch_records())
        
        assert len(records) == 1
        assert records[0][0] == "1"
    
    @patch('production_impl.requests.post')
    def test_multiple_batches(self, mock_post):
        """Test scrolling through multiple batches"""
        # Three responses: two with data, one empty
        response1 = Mock()
        response1.status_code = 200
        response1.json.return_value = {
            "hits": {"hits": [{"_id": "1", "_source": {"data": "batch1"}}]},
            "_scroll_id": "scroll1"
        }
        
        response2 = Mock()
        response2.status_code = 200
        response2.json.return_value = {
            "hits": {"hits": [{"_id": "2", "_source": {"data": "batch2"}}]},
            "_scroll_id": "scroll2"
        }
        
        response3 = Mock()
        response3.status_code = 200
        response3.json.return_value = {
            "hits": {"hits": []},
            "_scroll_id": "scroll3"
        }
        
        mock_post.side_effect = [response1, response2, response3]
        
        source = ElasticsearchSource(
            es_url="http://localhost:9200/test/_search",
            es_user="user",
            es_pass="pass",
            batch_size=1
        )
        
        records = list(source.fetch_records())
        
        assert len(records) == 2
        assert records[0][0] == "1"
        assert records[1][0] == "2"


class TestMySQLSinkEdgeCases:
    """Test edge cases in MySQLSink"""
    
    @patch('production_impl.mysql.connector.pooling.MySQLConnectionPool')
    def test_error_handling_detailed(self, mock_pool_class):
        """Test detailed error handling in insert"""
        mock_cursor = Mock()
        mock_conn = Mock()
        mock_conn.cursor.return_value = mock_cursor
        mock_pool = Mock()
        mock_pool.get_connection.return_value = mock_conn
        mock_pool_class.return_value = mock_pool
        
        sink = MySQLSink(
            host="localhost",
            user="root",
            password="password",
            database="testdb",
            table="testtable"
        )
        
        # Simulate various error conditions
        mock_cursor.execute.side_effect = [
            None,  # First succeeds (rowcount=1)
            Exception("Connection lost"),  # Second fails
            None,  # Third succeeds
        ]
        mock_cursor.rowcount = 1
        
        result1 = sink.insert_record("1", '{"data": "test1"}')
        assert result1 is True
        
        result2 = sink.insert_record("2", '{"data": "test2"}')
        assert result2 is False
        
        mock_cursor.rowcount = 1
        result3 = sink.insert_record("3", '{"data": "test3"}')
        assert result3 is True
        
        stats = sink.get_stats()
        assert stats["inserted"] == 2
        assert stats["errors"] == 1
    
    @patch('production_impl.mysql.connector.pooling.MySQLConnectionPool')
    def test_commit_logging(self, mock_pool_class):
        """Test that commit logs stats (commit is a no-op, commits happen per-record)"""
        mock_cursor = Mock()
        mock_cursor.rowcount = 1
        mock_conn = Mock()
        mock_conn.cursor.return_value = mock_cursor
        mock_pool = Mock()
        mock_pool.get_connection.return_value = mock_conn
        mock_pool_class.return_value = mock_pool

        sink = MySQLSink(
            host="localhost",
            user="root",
            password="password",
            database="testdb",
            table="testtable"
        )

        # Insert calls commit once per record
        sink.insert_record("1", '{"data": "test"}')
        assert mock_conn.commit.call_count == 1

        # sink.commit() is a no-op that just logs, doesn't call conn.commit()
        sink.commit()
        sink.commit()

        # Commit count should still be 1 (from insert_record)
        assert mock_conn.commit.call_count == 1
    
    @patch('production_impl.mysql.connector.pooling.MySQLConnectionPool')
    def test_stats_copy_independence(self, mock_pool_class):
        """Test that get_stats returns independent copy"""
        mock_cursor = Mock()
        mock_cursor.rowcount = 1
        mock_conn = Mock()
        mock_conn.cursor.return_value = mock_cursor
        mock_pool = Mock()
        mock_pool.get_connection.return_value = mock_conn
        mock_pool_class.return_value = mock_pool
        
        sink = MySQLSink(
            host="localhost",
            user="root",
            password="password",
            database="testdb",
            table="testtable"
        )
        
        sink.insert_record("1", '{"data": "test"}')
        
        stats1 = sink.get_stats()
        stats1["inserted"] = 999  # Modify returned stats
        
        stats2 = sink.get_stats()
        
        # Original stats should be unchanged
        assert stats2["inserted"] == 1
        assert stats1["inserted"] == 999


class TestProductionImplIntegration:
    """Integration tests for production implementations"""
    
    @patch('production_impl.mysql.connector.pooling.MySQLConnectionPool')
    @patch('production_impl.requests.post')
    def test_full_es_to_mysql_flow(self, mock_post, mock_pool_class):
        """Test complete ES -> MySQL flow with all edge cases"""
        # Setup ES mock with multiple batches
        batch1 = Mock()
        batch1.status_code = 200
        batch1.json.return_value = {
            "hits": {"hits": [
                {"_id": "1", "_source": {"data": "test1"}},
                {"_id": "2", "_source": {"data": "test2"}}
            ]},
            "_scroll_id": "scroll1"
        }

        batch2 = Mock()
        batch2.status_code = 200
        batch2.json.return_value = {
            "hits": {"hits": [
                {"_id": "3", "_source": {"data": "test3"}}
            ]},
            "_scroll_id": "scroll2"
        }

        empty = Mock()
        empty.status_code = 200
        empty.json.return_value = {
            "hits": {"hits": []},
            "_scroll_id": "scroll3"
        }

        mock_post.side_effect = [batch1, batch2, empty]

        # Setup MySQL mock with some errors
        mock_cursor = Mock()
        mock_conn = Mock()
        mock_conn.cursor.return_value = mock_cursor
        mock_pool = Mock()
        mock_pool.get_connection.return_value = mock_conn
        mock_pool_class.return_value = mock_pool
        
        # First two inserts succeed, third fails
        mock_cursor.execute.side_effect = [
            None,  # Record 1: success
            None,  # Record 2: success
            Exception("Deadlock"),  # Record 3: error
        ]
        mock_cursor.rowcount = 1
        
        # Create source and sink
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
        
        # Run the pipeline manually
        for record_id, content in source.fetch_records():
            sink.insert_record(record_id, content)
        
        sink.commit()
        
        stats = sink.get_stats()
        assert stats["inserted"] == 2
        assert stats["errors"] == 1
        
        source.close()
        sink.close()


if __name__ == "__main__":  # pragma: no cover
    pytest.main([__file__, "-v"])
