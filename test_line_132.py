"""
THE ABSOLUTE FINAL LINE - Line 132 in pipeline.py

Covers: Multi-threaded worker when insert returns False (skipped)

Author: Mac McAllorum
"""
import pytest
import tempfile
import csv
import os
from unittest.mock import Mock
from test_impl import CSVSource
from pipeline import DataPipeline


class TestPipelineWorkerSkipped:
    """Test the worker skipped branch (line 132 in pipeline.py)"""
    
    def test_multithreaded_worker_with_skips(self):
        """
        Test multi-threaded pipeline where sink returns False for some records.
        This triggers the else branch: worker_stats["skipped"] += 1 (line 132)
        """
        # Create CSV with several records
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            writer = csv.DictWriter(f, fieldnames=["id", "data"])
            writer.writeheader()
            for i in range(10):
                writer.writerow({"id": str(i), "data": f"test{i}"})
            csv_path = f.name
        
        try:
            source = CSVSource(csv_path)
            
            # Create a mock sink that returns False for records 3, 5, 7 (skipped)
            mock_sink = Mock()
            mock_sink.commit = Mock()
            mock_sink.close = Mock()
            
            # Track which records to skip
            skip_ids = {'3', '5', '7'}
            def insert_with_skips(record_id, content):
                # Return False for skip_ids, True otherwise
                return record_id not in skip_ids
            
            mock_sink.insert_record.side_effect = insert_with_skips
            mock_sink.get_stats.return_value = {"inserted": 7, "skipped": 3, "errors": 0}
            
            # Use multi-threading - THIS will trigger line 132 when insert returns False
            pipeline = DataPipeline(source, mock_sink, num_threads=2)
            stats = pipeline.run()
            pipeline.cleanup()
            
            # Verify skips were counted
            assert mock_sink.insert_record.call_count == 10
            assert stats["inserted"] == 7
            assert stats["skipped"] == 3  # ✅ Line 132 covered!
            
            print(f"✅ Line 132 COVERED! Multi-threaded workers processed skips correctly!")
            
        finally:
            if os.path.exists(csv_path):
                os.unlink(csv_path)


if __name__ == "__main__":  # pragma: no cover
    pytest.main([__file__, "-v", "-s"])
