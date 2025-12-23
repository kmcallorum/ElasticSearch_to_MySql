"""
Test suite for the data pipeline with dependency injection

Author: Kevin McAllorum (kevin_mcallorum@linux.com)
GitHub: github.com/kmcallorum
License: MIT
"""
import pytest
import json
import os
import tempfile
import csv
from pipeline import DataPipeline
from test_impl import CSVSource, FileSink, JSONLSink
from data_interfaces import DataSource, DataSink


# Test fixtures
@pytest.fixture
def temp_dir():
    """Create a temporary directory for test files"""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


@pytest.fixture
def sample_csv_file(temp_dir):
    """Create a sample CSV file for testing"""
    csv_path = os.path.join(temp_dir, "test_data.csv")
    
    with open(csv_path, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=["id", "name", "value", "timestamp"])
        writer.writeheader()
        writer.writerow({"id": "1", "name": "Alice", "value": "100", "timestamp": "2024-01-01"})
        writer.writerow({"id": "2", "name": "Bob", "value": "200", "timestamp": "2024-01-02"})
        writer.writerow({"id": "3", "name": "Charlie", "value": "300", "timestamp": "2024-01-03"})
        writer.writerow({"id": "4", "name": "Diana", "value": "400", "timestamp": "2024-01-04"})
        writer.writerow({"id": "5", "name": "Eve", "value": "500", "timestamp": "2024-01-05"})
    
    return csv_path


@pytest.fixture
def sample_csv_with_json(temp_dir):
    """Create a CSV file with JSON content column"""
    csv_path = os.path.join(temp_dir, "test_json_data.csv")
    
    with open(csv_path, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=["id", "content"])
        writer.writeheader()
        writer.writerow({"id": "1", "content": json.dumps({"name": "Alice", "value": 100})})
        writer.writerow({"id": "2", "content": json.dumps({"name": "Bob", "value": 200})})
        writer.writerow({"id": "3", "content": json.dumps({"name": "Charlie", "value": 300})})
    
    return csv_path


@pytest.fixture
def sample_csv_with_duplicates(temp_dir):
    """Create a CSV file with duplicate IDs"""
    csv_path = os.path.join(temp_dir, "test_duplicates.csv")
    
    with open(csv_path, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=["id", "data"])
        writer.writeheader()
        writer.writerow({"id": "1", "data": "first"})
        writer.writerow({"id": "2", "data": "second"})
        writer.writerow({"id": "1", "data": "duplicate"})  # Duplicate
        writer.writerow({"id": "3", "data": "third"})
        writer.writerow({"id": "2", "data": "another_duplicate"})  # Duplicate
    
    return csv_path


# Basic pipeline tests
class TestBasicPipeline:
    """Test basic pipeline functionality"""
    
    def test_simple_csv_to_file(self, sample_csv_file, temp_dir):
        """Test simple CSV to file pipeline"""
        output_path = os.path.join(temp_dir, "output.jsonl")
        
        source = CSVSource(sample_csv_file)
        sink = FileSink(output_path)
        pipeline = DataPipeline(source, sink, num_threads=1)
        
        stats = pipeline.run()
        pipeline.cleanup()
        
        assert stats["inserted"] == 5
        assert stats["skipped"] == 0
        assert stats["errors"] == 0
        
        # Verify output file
        assert os.path.exists(output_path)
        with open(output_path, 'r') as f:
            lines = f.readlines()
            assert len(lines) == 5
    
    def test_csv_with_limit(self, sample_csv_file, temp_dir):
        """Test CSV source with limit parameter"""
        output_path = os.path.join(temp_dir, "output_limited.jsonl")
        
        source = CSVSource(sample_csv_file)
        sink = FileSink(output_path)
        pipeline = DataPipeline(source, sink, num_threads=1)
        
        stats = pipeline.run(query_params={"limit": 3})
        pipeline.cleanup()
        
        assert stats["inserted"] == 3
        
        with open(output_path, 'r') as f:
            lines = f.readlines()
            assert len(lines) == 3


class TestDuplicateHandling:
    """Test duplicate record handling"""
    
    def test_duplicate_ids_are_skipped(self, sample_csv_with_duplicates, temp_dir):
        """Test that duplicate IDs are properly skipped"""
        output_path = os.path.join(temp_dir, "output_no_dupes.jsonl")
        
        source = CSVSource(sample_csv_with_duplicates)
        sink = FileSink(output_path)
        pipeline = DataPipeline(source, sink, num_threads=1)
        
        stats = pipeline.run()
        pipeline.cleanup()
        
        assert stats["inserted"] == 3  # Only unique IDs
        assert stats["skipped"] == 2  # Two duplicates
        
        # Verify only unique records in output
        with open(output_path, 'r') as f:
            lines = f.readlines()
            assert len(lines) == 3
            ids = [json.loads(line)["id"] for line in lines]
            assert ids == ["1", "2", "3"]


class TestJSONHandling:
    """Test JSON content handling"""
    
    def test_csv_with_json_content(self, sample_csv_with_json, temp_dir):
        """Test CSV with pre-formatted JSON content"""
        output_path = os.path.join(temp_dir, "output_json.jsonl")
        
        source = CSVSource(sample_csv_with_json, content_column="content")
        sink = JSONLSink(output_path)
        pipeline = DataPipeline(source, sink, num_threads=1)
        
        stats = pipeline.run()
        pipeline.cleanup()
        
        assert stats["inserted"] == 3
        
        # Verify JSON structure
        with open(output_path, 'r') as f:
            for line in f:
                record = json.loads(line)
                assert "id" in record
                assert "name" in record
                assert "value" in record


class TestStatistics:
    """Test statistics tracking"""
    
    def test_stats_accuracy(self, sample_csv_with_duplicates, temp_dir):
        """Test that statistics are accurately tracked"""
        output_path = os.path.join(temp_dir, "output_stats.jsonl")
        
        source = CSVSource(sample_csv_with_duplicates)
        sink = FileSink(output_path)
        pipeline = DataPipeline(source, sink, num_threads=1)
        
        stats = pipeline.run()
        pipeline.cleanup()
        
        # Verify stats match expectations
        total = stats["inserted"] + stats["skipped"] + stats["errors"]
        assert total == 5  # Total rows in CSV
        assert stats["inserted"] == 3
        assert stats["skipped"] == 2
        assert stats["errors"] == 0


class TestErrorHandling:
    """Test error handling scenarios"""
    
    def test_missing_csv_file(self, temp_dir):
        """Test handling of missing source file"""
        nonexistent = os.path.join(temp_dir, "nonexistent.csv")
        output_path = os.path.join(temp_dir, "output.jsonl")
        
        source = CSVSource(nonexistent)
        sink = FileSink(output_path)
        pipeline = DataPipeline(source, sink, num_threads=1)
        
        with pytest.raises(FileNotFoundError):
            pipeline.run()
    
    def test_invalid_json_in_content_column(self, temp_dir):
        """Test handling of invalid JSON in content column"""
        csv_path = os.path.join(temp_dir, "invalid_json.csv")
        output_path = os.path.join(temp_dir, "output.jsonl")
        
        # Create CSV with invalid JSON in content column
        with open(csv_path, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=["id", "content"])
            writer.writeheader()
            writer.writerow({"id": "1", "content": "not valid json{{"})
            writer.writerow({"id": "2", "content": '{"valid": "json"}'})
        
        source = CSVSource(csv_path, id_column="id", content_column="content")
        sink = FileSink(output_path)
        pipeline = DataPipeline(source, sink, num_threads=1)
        
        stats = pipeline.run()
        pipeline.cleanup()
        
        # Both records should be inserted (invalid JSON wrapped in row JSON)
        assert stats["inserted"] == 2
        assert stats["errors"] == 0
    
    def test_invalid_csv_structure(self, temp_dir):
        """Test handling of CSV with missing ID column"""
        csv_path = os.path.join(temp_dir, "invalid.csv")
        output_path = os.path.join(temp_dir, "output.jsonl")
        
        # Create CSV without ID column
        with open(csv_path, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=["name", "value"])
            writer.writeheader()
            writer.writerow({"name": "Alice", "value": "100"})
        
        source = CSVSource(csv_path, id_column="id")
        sink = FileSink(output_path)
        pipeline = DataPipeline(source, sink, num_threads=1)
        
        stats = pipeline.run()
        pipeline.cleanup()
        
        # Should skip rows without ID
        assert stats["inserted"] == 0


class TestPipelineIntegration:
    """Integration tests for the complete pipeline"""
    
    def test_end_to_end_csv_to_jsonl(self, sample_csv_file, temp_dir):
        """Complete end-to-end test: CSV -> Pipeline -> JSONL"""
        output_path = os.path.join(temp_dir, "final_output.jsonl")
        
        source = CSVSource(sample_csv_file)
        sink = JSONLSink(output_path)
        pipeline = DataPipeline(source, sink, num_threads=1)
        
        stats = pipeline.run()
        pipeline.cleanup()
        
        # Verify all records processed
        assert stats["inserted"] == 5
        
        # Verify output format and content
        with open(output_path, 'r') as f:
            records = [json.loads(line) for line in f]
            
            assert len(records) == 5
            
            # Check first record structure
            first = records[0]
            assert first["id"] == "1"
            assert first["name"] == "Alice"
            assert first["value"] == "100"
            
            # Check all IDs are present
            ids = [r["id"] for r in records]
            assert ids == ["1", "2", "3", "4", "5"]
    
    def test_idempotency(self, sample_csv_file, temp_dir):
        """Test that running pipeline twice produces same results"""
        output_path = os.path.join(temp_dir, "idempotent.jsonl")
        
        # First run
        source1 = CSVSource(sample_csv_file)
        sink1 = FileSink(output_path, mode='w')
        pipeline1 = DataPipeline(source1, sink1, num_threads=1)
        stats1 = pipeline1.run()
        pipeline1.cleanup()
        
        # Count records from first run
        with open(output_path, 'r') as f:
            first_run_lines = f.readlines()
        
        # Second run (overwrite mode for consistency)
        source2 = CSVSource(sample_csv_file)
        sink2 = FileSink(output_path, mode='w')
        pipeline2 = DataPipeline(source2, sink2, num_threads=1)
        stats2 = pipeline2.run()
        pipeline2.cleanup()
        
        # Count records from second run
        with open(output_path, 'r') as f:
            second_run_lines = f.readlines()
        
        # Both runs should produce same stats and same number of records
        assert stats1["inserted"] == stats2["inserted"] == 5
        assert len(first_run_lines) == len(second_run_lines) == 5
        
        # Content should be identical
        assert first_run_lines == second_run_lines


# Run tests with: pytest test_pipeline.py -v
if __name__ == "__main__":  # pragma: no cover
    pytest.main([__file__, "-v"])
