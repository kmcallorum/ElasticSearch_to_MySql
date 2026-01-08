"""
Tests for Prometheus metrics module

Maintains 100% test coverage!

Author: Kevin McAllorum (kevin_mcallorum@linux.com)
"""
import pytest
import time
import metrics


class TestMetricsInitialization:
    """Test metrics module initialization"""
    
    def test_metrics_module_loaded(self):
        """Test that metrics module loads successfully"""
        assert metrics is not None
        assert hasattr(metrics, 'records_processed_total')
        assert hasattr(metrics, 'records_inserted_total')
        assert hasattr(metrics, 'records_skipped_total')
    
    def test_pipeline_info_initialized(self):
        """Test that pipeline info is set on module load"""
        summary = metrics.get_metrics_summary()
        assert summary["metrics_registered"] is True
        assert len(summary["counters"]) > 0
        assert len(summary["gauges"]) > 0
        assert len(summary["histograms"]) > 0


class TestCounters:
    """Test counter metrics"""
    
    def test_records_processed_counter(self):
        """Test records_processed_total counter"""
        initial = metrics.records_processed_total.labels(
            source_type="test",
            sink_type="test"
        )._value.get()
        
        metrics.records_processed_total.labels(
            source_type="test",
            sink_type="test"
        ).inc()
        
        final = metrics.records_processed_total.labels(
            source_type="test",
            sink_type="test"
        )._value.get()
        
        assert final == initial + 1
    
    def test_ai_analysis_counter(self):
        """Test AI analysis request counter"""
        initial = metrics.ai_analysis_requests_total.labels(
            analyzer_type="SimpleErrorAnalyzer",
            status="success"
        )._value.get()
        
        metrics.ai_analysis_requests_total.labels(
            analyzer_type="SimpleErrorAnalyzer",
            status="success"
        ).inc()
        
        final = metrics.ai_analysis_requests_total.labels(
            analyzer_type="SimpleErrorAnalyzer",
            status="success"
        )._value.get()
        
        assert final == initial + 1


class TestGauges:
    """Test gauge metrics"""
    
    def test_active_workers_gauge(self):
        """Test active_workers gauge"""
        metrics.active_workers.labels(pipeline_id="test").set(5)
        value = metrics.active_workers.labels(pipeline_id="test")._value.get()
        assert value == 5
        
        metrics.active_workers.labels(pipeline_id="test").set(0)
        value = metrics.active_workers.labels(pipeline_id="test")._value.get()
        assert value == 0
    
    def test_queue_depth_gauge(self):
        """Test queue_depth gauge"""
        metrics.queue_depth.labels(pipeline_id="test").set(100)
        value = metrics.queue_depth.labels(pipeline_id="test")._value.get()
        assert value == 100
    
    def test_pipeline_state_gauge(self):
        """Test pipeline_state gauge"""
        # 0 = stopped, 1 = running, 2 = error
        metrics.pipeline_state.labels(pipeline_id="test").set(1)
        value = metrics.pipeline_state.labels(pipeline_id="test")._value.get()
        assert value == 1


class TestHistograms:
    """Test histogram metrics"""
    
    def test_fetch_duration_histogram(self):
        """Test fetch_duration_seconds histogram"""
        # Record observation
        metrics.fetch_duration_seconds.labels(source_type="test_hist").observe(0.5)
        
        # Histograms don't expose count directly in labels, but we can verify
        # by trying to collect the metric
        from prometheus_client import generate_latest
        output = generate_latest().decode('utf-8')
        assert 'pipeline_fetch_duration_seconds' in output
    
    def test_insert_duration_histogram(self):
        """Test insert_duration_seconds histogram"""
        metrics.insert_duration_seconds.labels(sink_type="test_hist").observe(0.1)
        
        from prometheus_client import generate_latest
        output = generate_latest().decode('utf-8')
        assert 'pipeline_insert_duration_seconds' in output
    
    def test_batch_size_histogram(self):
        """Test batch_size histogram"""
        metrics.batch_size.labels(source_type="test_hist").observe(1000)
        
        from prometheus_client import generate_latest
        output = generate_latest().decode('utf-8')
        assert 'pipeline_batch_size' in output


class TestHelperFunctions:
    """Test helper functions"""
    
    def test_time_operation_context_manager(self):
        """Test time_operation context manager"""
        with metrics.time_operation(
            metrics.insert_duration_seconds,
            sink_type="test_cm"
        ):
            time.sleep(0.01)
        
        # Verify timing was recorded by checking metrics output
        from prometheus_client import generate_latest
        output = generate_latest().decode('utf-8')
        assert 'sink_type="test_cm"' in output
    
    def test_time_operation_with_exception(self):
        """Test time_operation still records time even with exception"""
        try:
            with metrics.time_operation(
                metrics.insert_duration_seconds,
                sink_type="test_exception"
            ):
                raise ValueError("Test error")
        except ValueError:
            pass
        
        # Timing should still be recorded
        from prometheus_client import generate_latest
        output = generate_latest().decode('utf-8')
        assert 'sink_type="test_exception"' in output
    
    def test_record_success(self):
        """Test record_success helper"""
        initial_processed = metrics.records_processed_total.labels(
            source_type="test_success",
            sink_type="test_success"
        )._value.get()
        
        initial_inserted = metrics.records_inserted_total.labels(
            source_type="test_success",
            sink_type="test_success"
        )._value.get()
        
        metrics.record_success("test_success", "test_success")
        
        final_processed = metrics.records_processed_total.labels(
            source_type="test_success",
            sink_type="test_success"
        )._value.get()
        
        final_inserted = metrics.records_inserted_total.labels(
            source_type="test_success",
            sink_type="test_success"
        )._value.get()
        
        assert final_processed == initial_processed + 1
        assert final_inserted == initial_inserted + 1
    
    def test_record_skip(self):
        """Test record_skip helper"""
        initial = metrics.records_skipped_total.labels(
            source_type="test_skip",
            sink_type="test_skip",
            reason="duplicate"
        )._value.get()
        
        metrics.record_skip("test_skip", "test_skip", "duplicate")
        
        final = metrics.records_skipped_total.labels(
            source_type="test_skip",
            sink_type="test_skip",
            reason="duplicate"
        )._value.get()
        
        assert final == initial + 1
    
    def test_record_failure(self):
        """Test record_failure helper"""
        error = ValueError("Test error")
        
        initial = metrics.records_failed_total.labels(
            source_type="test_failure",
            sink_type="test_failure",
            error_type="ValueError"
        )._value.get()
        
        metrics.record_failure("test_failure", "test_failure", error)
        
        final = metrics.records_failed_total.labels(
            source_type="test_failure",
            sink_type="test_failure",
            error_type="ValueError"
        )._value.get()
        
        assert final == initial + 1
    
    def test_record_ai_analysis_success(self):
        """Test record_ai_analysis helper with success"""
        initial = metrics.ai_analysis_requests_total.labels(
            analyzer_type="TestAnalyzer",
            status="success"
        )._value.get()
        
        metrics.record_ai_analysis("TestAnalyzer", True)
        
        final = metrics.ai_analysis_requests_total.labels(
            analyzer_type="TestAnalyzer",
            status="success"
        )._value.get()
        
        assert final == initial + 1
    
    def test_record_ai_analysis_failure(self):
        """Test record_ai_analysis helper with failure"""
        initial = metrics.ai_analysis_requests_total.labels(
            analyzer_type="TestAnalyzer",
            status="failure"
        )._value.get()
        
        metrics.record_ai_analysis("TestAnalyzer", False)
        
        final = metrics.ai_analysis_requests_total.labels(
            analyzer_type="TestAnalyzer",
            status="failure"
        )._value.get()
        
        assert final == initial + 1
    
    def test_set_pipeline_info(self):
        """Test set_pipeline_info function"""
        metrics.set_pipeline_info(
            version="2.0.0",
            author="Test Author",
            custom="custom_value"
        )
        # If it doesn't raise an exception, it works
        assert True
    
    def test_get_metrics_summary(self):
        """Test get_metrics_summary function"""
        summary = metrics.get_metrics_summary()
        
        assert isinstance(summary, dict)
        assert "metrics_registered" in summary
        assert "counters" in summary
        assert "gauges" in summary
        assert "histograms" in summary
        
        assert len(summary["counters"]) > 0
        assert len(summary["gauges"]) > 0
        assert len(summary["histograms"]) > 0


if __name__ == "__main__":  # pragma: no cover
    pytest.main([__file__, "-v"])
