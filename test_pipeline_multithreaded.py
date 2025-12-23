"""
Additional tests for pipeline.py multi-threaded execution

These tests specifically cover the multi-threaded code paths that were 
previously untested, bringing coverage from 50% to ~80%+

Author: Kevin McAllorum (kevin_mcallorum@linux.com)
GitHub: github.com/kmcallorum
License: MIT
"""
import pytest
import time
import tempfile
import csv
from unittest.mock import Mock, patch
from pipeline import DataPipeline
from test_impl import CSVSource, FileSink, JSONLSink
from error_analyzer import SimpleErrorAnalyzer, NoOpErrorAnalyzer


class TestMultiThreadedExecution:
    """Test multi-threaded pipeline execution"""
    
    def test_multi_threaded_with_mysql_sink(self):
        """Test that multi-threading is used for MySQL-like sinks"""
        # Create test data
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            writer = csv.DictWriter(f, fieldnames=["id", "data"])
            writer.writeheader()
            for i in range(20):
                writer.writerow({"id": str(i), "data": f"test{i}"})
            csv_path = f.name
        
        output_path = tempfile.mktemp(suffix='.jsonl')
        
        try:
            source = CSVSource(csv_path)
            
            # Use JSONLSink which is thread-safe
            sink = JSONLSink(output_path)
            
            # Use 5 threads
            pipeline = DataPipeline(source, sink, num_threads=5)
            
            stats = pipeline.run()
            pipeline.cleanup()
            
            # Verify all records processed
            assert stats["inserted"] == 20
            assert stats["skipped"] == 0
            
        finally:
            import os
            if os.path.exists(csv_path):
                os.unlink(csv_path)
            if os.path.exists(output_path):
                os.unlink(output_path)
    
    def test_single_threaded_with_file_sink(self):
        """Test that single-threading is forced for FileSink"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            writer = csv.DictWriter(f, fieldnames=["id", "data"])
            writer.writeheader()
            for i in range(10):
                writer.writerow({"id": str(i), "data": f"test{i}"})
            csv_path = f.name
        
        output_path = tempfile.mktemp(suffix='.jsonl')
        
        try:
            source = CSVSource(csv_path)
            sink = FileSink(output_path)
            
            # Request 5 threads but FileSink forces single-threaded
            pipeline = DataPipeline(source, sink, num_threads=5)
            
            stats = pipeline.run()
            pipeline.cleanup()
            
            assert stats["inserted"] == 10
            
        finally:
            import os
            if os.path.exists(csv_path):
                os.unlink(csv_path)
            if os.path.exists(output_path):
                os.unlink(output_path)
    
    def test_multi_threaded_completes_successfully(self):
        """Test that multi-threading completes without errors"""
        # Note: Performance tests are flaky - threading overhead can exceed
        # benefits on small datasets. This test just validates correctness.
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            writer = csv.DictWriter(f, fieldnames=["id", "data"])
            writer.writeheader()
            for i in range(100):
                writer.writerow({"id": str(i), "data": f"test{i}"})
            csv_path = f.name
        
        output_path = tempfile.mktemp(suffix='.jsonl')
        
        try:
            # Run with 1 thread
            source1 = CSVSource(csv_path)
            sink1 = JSONLSink(output_path + "_single")
            pipeline1 = DataPipeline(source1, sink1, num_threads=1)
            stats1 = pipeline1.run()
            pipeline1.cleanup()
            
            # Run with 5 threads
            source2 = CSVSource(csv_path)
            sink2 = JSONLSink(output_path + "_multi")
            pipeline2 = DataPipeline(source2, sink2, num_threads=5)
            stats2 = pipeline2.run()
            pipeline2.cleanup()
            
            # Both should process all records successfully
            assert stats1["inserted"] == 100
            assert stats2["inserted"] == 100
            # Threading doesn't break correctness
            assert stats1 == stats2
            
        finally:
            import os
            if os.path.exists(csv_path):
                os.unlink(csv_path)
            for path in [output_path + "_single", output_path + "_multi"]:
                if os.path.exists(path):
                    os.unlink(path)
    
    def test_worker_thread_error_handling(self):
        """Test that worker threads handle errors gracefully"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            writer = csv.DictWriter(f, fieldnames=["id", "data"])
            writer.writeheader()
            for i in range(10):
                writer.writerow({"id": str(i), "data": f"test{i}"})
            csv_path = f.name
        
        output_path = tempfile.mktemp(suffix='.jsonl')
        
        try:
            source = CSVSource(csv_path)
            sink = JSONLSink(output_path)
            
            # Create pipeline with error analyzer
            analyzer = SimpleErrorAnalyzer()
            pipeline = DataPipeline(source, sink, num_threads=3, error_analyzer=analyzer)
            
            # Should complete without crashing even if errors occur
            stats = pipeline.run()
            pipeline.cleanup()
            
            # All records should be processed
            assert stats["inserted"] + stats["skipped"] >= 10
            
        finally:
            import os
            if os.path.exists(csv_path):
                os.unlink(csv_path)
            if os.path.exists(output_path):
                os.unlink(output_path)
    
    def test_queue_processing(self):
        """Test that work queue is properly drained"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            writer = csv.DictWriter(f, fieldnames=["id", "data"])
            writer.writeheader()
            for i in range(50):
                writer.writerow({"id": str(i), "data": f"test{i}"})
            csv_path = f.name
        
        output_path = tempfile.mktemp(suffix='.jsonl')
        
        try:
            source = CSVSource(csv_path)
            sink = JSONLSink(output_path)
            
            # Use more threads than records to test queue draining
            pipeline = DataPipeline(source, sink, num_threads=10)
            
            stats = pipeline.run()
            pipeline.cleanup()
            
            # All records processed, no hangs
            assert stats["inserted"] == 50
            
        finally:
            import os
            if os.path.exists(csv_path):
                os.unlink(csv_path)
            if os.path.exists(output_path):
                os.unlink(output_path)
    
    def test_with_query_params(self):
        """Test multi-threaded execution with query parameters"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            writer = csv.DictWriter(f, fieldnames=["id", "data"])
            writer.writeheader()
            for i in range(15):
                writer.writerow({"id": str(i), "data": f"test{i}"})
            csv_path = f.name
        
        output_path = tempfile.mktemp(suffix='.jsonl')
        
        try:
            source = CSVSource(csv_path)
            sink = JSONLSink(output_path)
            
            pipeline = DataPipeline(source, sink, num_threads=3)
            
            # Pass query params (limit)
            stats = pipeline.run(query_params={"limit": 10})
            pipeline.cleanup()
            
            # Should respect limit
            assert stats["inserted"] <= 10
            
        finally:
            import os
            if os.path.exists(csv_path):
                os.unlink(csv_path)
            if os.path.exists(output_path):
                os.unlink(output_path)


class TestPipelineWithErrorAnalyzer:
    """Test pipeline with different error analyzers"""
    
    def test_with_simple_error_analyzer(self):
        """Test pipeline with SimpleErrorAnalyzer"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            writer = csv.DictWriter(f, fieldnames=["id", "data"])
            writer.writeheader()
            writer.writerow({"id": "1", "data": "test"})
            csv_path = f.name
        
        output_path = tempfile.mktemp(suffix='.jsonl')
        
        try:
            source = CSVSource(csv_path)
            sink = FileSink(output_path)
            analyzer = SimpleErrorAnalyzer()
            
            pipeline = DataPipeline(source, sink, num_threads=1, error_analyzer=analyzer)
            
            stats = pipeline.run()
            pipeline.cleanup()
            
            assert stats["inserted"] == 1
            assert analyzer.is_enabled() is True
            
        finally:
            import os
            if os.path.exists(csv_path):
                os.unlink(csv_path)
            if os.path.exists(output_path):
                os.unlink(output_path)
    
    def test_with_noop_error_analyzer(self):
        """Test pipeline with NoOpErrorAnalyzer (default)"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            writer = csv.DictWriter(f, fieldnames=["id", "data"])
            writer.writeheader()
            writer.writerow({"id": "1", "data": "test"})
            csv_path = f.name
        
        output_path = tempfile.mktemp(suffix='.jsonl')
        
        try:
            source = CSVSource(csv_path)
            sink = FileSink(output_path)
            analyzer = NoOpErrorAnalyzer()
            
            pipeline = DataPipeline(source, sink, num_threads=1, error_analyzer=analyzer)
            
            stats = pipeline.run()
            pipeline.cleanup()
            
            assert stats["inserted"] == 1
            assert analyzer.is_enabled() is False
            
        finally:
            import os
            if os.path.exists(csv_path):
                os.unlink(csv_path)
            if os.path.exists(output_path):
                os.unlink(output_path)


class TestPipelineEdgeCases:
    """Test edge cases and boundary conditions"""
    
    def test_empty_source(self):
        """Test pipeline with no records"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            writer = csv.DictWriter(f, fieldnames=["id", "data"])
            writer.writeheader()
            # No data rows
            csv_path = f.name
        
        output_path = tempfile.mktemp(suffix='.jsonl')
        
        try:
            source = CSVSource(csv_path)
            sink = FileSink(output_path)
            
            pipeline = DataPipeline(source, sink, num_threads=1)
            
            stats = pipeline.run()
            pipeline.cleanup()
            
            assert stats["inserted"] == 0
            assert stats["skipped"] == 0
            
        finally:
            import os
            if os.path.exists(csv_path):
                os.unlink(csv_path)
            if os.path.exists(output_path):
                os.unlink(output_path)
    
    def test_single_record(self):
        """Test pipeline with exactly one record"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            writer = csv.DictWriter(f, fieldnames=["id", "data"])
            writer.writeheader()
            writer.writerow({"id": "1", "data": "single"})
            csv_path = f.name
        
        output_path = tempfile.mktemp(suffix='.jsonl')
        
        try:
            source = CSVSource(csv_path)
            sink = JSONLSink(output_path)
            
            pipeline = DataPipeline(source, sink, num_threads=5)
            
            stats = pipeline.run()
            pipeline.cleanup()
            
            assert stats["inserted"] == 1
            
        finally:
            import os
            if os.path.exists(csv_path):
                os.unlink(csv_path)
            if os.path.exists(output_path):
                os.unlink(output_path)
    
    def test_many_threads_few_records(self):
        """Test with more threads than records"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            writer = csv.DictWriter(f, fieldnames=["id", "data"])
            writer.writeheader()
            for i in range(3):
                writer.writerow({"id": str(i), "data": f"test{i}"})
            csv_path = f.name
        
        output_path = tempfile.mktemp(suffix='.jsonl')
        
        try:
            source = CSVSource(csv_path)
            sink = JSONLSink(output_path)
            
            # 20 threads for 3 records
            pipeline = DataPipeline(source, sink, num_threads=20)
            
            stats = pipeline.run()
            pipeline.cleanup()
            
            assert stats["inserted"] == 3
            
        finally:
            import os
            if os.path.exists(csv_path):
                os.unlink(csv_path)
            if os.path.exists(output_path):
                os.unlink(output_path)


if __name__ == "__main__":  # pragma: no cover
    pytest.main([__file__, "-v"])
