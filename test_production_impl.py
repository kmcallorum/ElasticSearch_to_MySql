"""
Tests for production implementations - FIXED infinite loop issue

Author: Mac McAllorum (kevin_mcallorum@linux.com)
"""
import pytest
from unittest.mock import Mock, patch
import json
from production_impl import ElasticsearchSource, MySQLSink


class TestElasticsearchSource:
    """Test ElasticsearchSource with mocked requests"""
    
    @patch('production_impl.requests.post')
    def test_basic_fetch(self, mock_post):
        """Test basic record fetching from Elasticsearch"""
        # First call returns data, second call returns empty (ends loop)
        first_response = Mock()
        first_response.status_code = 200
        first_response.json.return_value = {
            "hits": {"hits": [
                {"_id": "1", "_source": {"data": "test1"}},
                {"_id": "2", "_source": {"data": "test2"}}
            ]},
            "_scroll_id": "scroll123"
        }
        
        empty_response = Mock()
        empty_response.status_code = 200
        empty_response.json.return_value = {
            "hits": {"hits": []},  # Empty to end the loop!
            "_scroll_id": "scroll123"
        }
        
        mock_post.side_effect = [first_response, empty_response]
        
        source = ElasticsearchSource(
            es_url="http://localhost:9200/test/_search",
            es_user="user",
            es_pass="pass",
            batch_size=10
        )
        
        records = list(source.fetch_records())
        
        assert len(records) == 2
        assert records[0][0] == "1"
        assert "test1" in records[0][1]
    
    @patch('production_impl.requests.post')
    def test_with_query_params(self, mock_post):
        """Test fetching with query parameters"""
        # Return empty immediately to avoid hanging
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
        
        query_params = {
            "gte": "2024-01-01T00:00:00",
            "lte": "2024-12-31T23:59:59"
        }
        list(source.fetch_records(query_params))
        
        # Verify query was built
        call_args = mock_post.call_args_list[0]
        sent_data = json.loads(call_args[1]['data'])
        assert "query" in sent_data
    
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
        
        records = list(source.fetch_records())
        assert len(records) == 0
    
    @patch('production_impl.requests.post')
    def test_scroll_pagination(self, mock_post):
        """Test scrolling across batches"""
        first = Mock()
        first.status_code = 200
        first.json.return_value = {
            "hits": {"hits": [{"_id": "1", "_source": {"data": "batch1"}}]},
            "_scroll_id": "scroll123"
        }
        
        second = Mock()
        second.status_code = 200
        second.json.return_value = {
            "hits": {"hits": []},  # Empty to end
            "_scroll_id": "scroll456"
        }
        
        mock_post.side_effect = [first, second]
        
        source = ElasticsearchSource(
            es_url="http://localhost:9200/test/_search",
            es_user="user",
            es_pass="pass"
        )
        
        records = list(source.fetch_records())
        assert len(records) == 1
    
    @patch('production_impl.requests.post')
    def test_error_handling_bad_status(self, mock_post):
        """Test error on bad status code"""
        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"
        mock_post.return_value = mock_response
        
        source = ElasticsearchSource(
            es_url="http://localhost:9200/test/_search",
            es_user="user",
            es_pass="pass"
        )
        
        with pytest.raises(Exception) as exc_info:
            list(source.fetch_records())
        
        assert "500" in str(exc_info.value)
    
    @patch('production_impl.requests.post')
    def test_close(self, mock_post):
        """Test close method"""
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
        
        list(source.fetch_records())
        source.close()
        assert True


class TestMySQLSink:
    """Test MySQLSink with mocked MySQL"""
    
    @patch('production_impl.mysql.connector.connect')
    def test_basic_insert(self, mock_connect):
        """Test basic insert"""
        mock_cursor = Mock()
        mock_cursor.rowcount = 1
        mock_conn = Mock()
        mock_conn.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_conn
        
        sink = MySQLSink(
            host="localhost", user="root", password="password",
            database="testdb", table="testtable"
        )
        
        result = sink.insert_record("123", '{"data": "test"}')
        assert result is True
    
    @patch('production_impl.mysql.connector.connect')
    def test_duplicate_handling(self, mock_connect):
        """Test duplicate detection"""
        mock_cursor = Mock()
        mock_conn = Mock()
        mock_conn.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_conn
        
        sink = MySQLSink(
            host="localhost", user="root", password="password",
            database="testdb", table="testtable"
        )
        
        mock_cursor.rowcount = 1
        result1 = sink.insert_record("123", '{"data": "test"}')
        assert result1 is True
        
        mock_cursor.rowcount = 0
        result2 = sink.insert_record("123", '{"data": "test2"}')
        assert result2 is False
        
        stats = sink.get_stats()
        assert stats["inserted"] == 1
        assert stats["skipped"] == 1
    
    @patch('production_impl.mysql.connector.connect')
    def test_commit(self, mock_connect):
        """Test commit"""
        mock_cursor = Mock()
        mock_cursor.rowcount = 1
        mock_conn = Mock()
        mock_conn.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_conn
        
        sink = MySQLSink(
            host="localhost", user="root", password="password",
            database="testdb", table="testtable"
        )
        
        sink.insert_record("123", '{"data": "test"}')
        sink.commit()
        mock_conn.commit.assert_called()
    
    @patch('production_impl.mysql.connector.connect')
    def test_close(self, mock_connect):
        """Test close"""
        mock_cursor = Mock()
        mock_conn = Mock()
        mock_conn.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_conn
        
        sink = MySQLSink(
            host="localhost", user="root", password="password",
            database="testdb", table="testtable"
        )
        
        sink.close()
        mock_cursor.close.assert_called_once()
        mock_conn.close.assert_called_once()
    
    @patch('production_impl.mysql.connector.connect')
    def test_error_handling(self, mock_connect):
        """Test error handling"""
        mock_cursor = Mock()
        mock_cursor.execute.side_effect = Exception("DB error")
        mock_conn = Mock()
        mock_conn.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_conn
        
        sink = MySQLSink(
            host="localhost", user="root", password="password",
            database="testdb", table="testtable"
        )
        
        result = sink.insert_record("123", '{"data": "test"}')
        assert result is False
        assert sink.get_stats()["errors"] == 1
    
    @patch('production_impl.mysql.connector.connect')
    def test_stats_tracking(self, mock_connect):
        """Test stats"""
        mock_cursor = Mock()
        mock_conn = Mock()
        mock_conn.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_conn
        
        sink = MySQLSink(
            host="localhost", user="root", password="password",
            database="testdb", table="testtable"
        )
        
        mock_cursor.rowcount = 1
        sink.insert_record("1", '{"data": "test1"}')
        mock_cursor.rowcount = 1
        sink.insert_record("2", '{"data": "test2"}')
        mock_cursor.rowcount = 0
        sink.insert_record("1", '{"data": "dup"}')
        
        stats = sink.get_stats()
        assert stats["inserted"] == 2
        assert stats["skipped"] == 1


class TestIntegration:
    """Integration test"""
    
    @patch('production_impl.mysql.connector.connect')
    @patch('production_impl.requests.post')
    def test_full_pipeline(self, mock_post, mock_connect):
        """Test ES -> MySQL pipeline"""
        # ES mock - return data then empty
        first = Mock()
        first.status_code = 200
        first.json.return_value = {
            "hits": {"hits": [
                {"_id": "1", "_source": {"data": "test1"}},
                {"_id": "2", "_source": {"data": "test2"}}
            ]},
            "_scroll_id": "scroll123"
        }
        
        empty = Mock()
        empty.status_code = 200
        empty.json.return_value = {
            "hits": {"hits": []},
            "_scroll_id": "scroll123"
        }
        
        mock_post.side_effect = [first, empty]
        
        # MySQL mock
        mock_cursor = Mock()
        mock_cursor.rowcount = 1
        mock_conn = Mock()
        mock_conn.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_conn
        
        # Run pipeline
        source = ElasticsearchSource(
            es_url="http://localhost:9200/test/_search",
            es_user="user",
            es_pass="pass"
        )
        
        sink = MySQLSink(
            host="localhost", user="root", password="password",
            database="testdb", table="testtable"
        )
        
        for record_id, content in source.fetch_records():
            sink.insert_record(record_id, content)
        
        sink.commit()
        
        stats = sink.get_stats()
        assert stats["inserted"] == 2
        
        source.close()
        sink.close()


if __name__ == "__main__":  # pragma: no cover
    pytest.main([__file__, "-v"])
