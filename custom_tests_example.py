"""
Example: Adding custom tests for specific business logic

This file shows how to extend the test suite with your own
domain-specific tests.
"""
import pytest
import os
import csv
import json
import tempfile
from pipeline import DataPipeline
from test_impl import CSVSource, FileSink


# ============================================================================
# Custom Test Fixture for Your Domain
# ============================================================================

@pytest.fixture
def customer_data_csv(tmp_path):
    """Sample customer data for testing"""
    csv_file = tmp_path / "customers.csv"
    
    with open(csv_file, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=["customer_id", "name", "email", "balance", "status"])
        writer.writeheader()
        
        # Active customers
        writer.writerow({"customer_id": "C001", "name": "Alice", "email": "alice@example.com", "balance": "1500.00", "status": "active"})
        writer.writerow({"customer_id": "C002", "name": "Bob", "email": "bob@example.com", "balance": "2500.50", "status": "active"})
        
        # Inactive customer
        writer.writerow({"customer_id": "C003", "name": "Charlie", "email": "charlie@example.com", "balance": "0.00", "status": "inactive"})
        
        # VIP customer (high balance)
        writer.writerow({"customer_id": "C004", "name": "Diana", "email": "diana@example.com", "balance": "50000.00", "status": "vip"})
        
        # Duplicate for testing
        writer.writerow({"customer_id": "C001", "name": "Alice Duplicate", "email": "alice2@example.com", "balance": "999.99", "status": "active"})
    
    return csv_file


@pytest.fixture
def transaction_data_csv(tmp_path):
    """Sample transaction data for testing"""
    csv_file = tmp_path / "transactions.csv"
    
    with open(csv_file, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=["txn_id", "customer_id", "amount", "type", "timestamp"])
        writer.writeheader()
        
        writer.writerow({"txn_id": "T001", "customer_id": "C001", "amount": "100.00", "type": "purchase", "timestamp": "2024-01-01T10:00:00"})
        writer.writerow({"txn_id": "T002", "customer_id": "C001", "amount": "50.00", "type": "refund", "timestamp": "2024-01-02T11:00:00"})
        writer.writerow({"txn_id": "T003", "customer_id": "C002", "amount": "250.00", "type": "purchase", "timestamp": "2024-01-03T12:00:00"})
    
    return csv_file


# ============================================================================
# Domain-Specific Tests
# ============================================================================

class TestCustomerDataMigration:
    """Tests specific to customer data migration scenarios"""
    
    def test_all_customers_migrated(self, customer_data_csv, tmp_path):
        """Verify all unique customers are migrated"""
        output_file = tmp_path / "customers_output.jsonl"
        
        source = CSVSource(str(customer_data_csv), id_column="customer_id")
        sink = FileSink(str(output_file))
        pipeline = DataPipeline(source, sink, num_threads=1)
        
        stats = pipeline.run()
        pipeline.cleanup()
        
        # Should have 4 unique customers (C001 duplicate skipped)
        assert stats["inserted"] == 4
        assert stats["skipped"] == 1
    
    def test_customer_email_format(self, customer_data_csv, tmp_path):
        """Verify all customers have valid email addresses"""
        output_file = tmp_path / "customers_output.jsonl"
        
        source = CSVSource(str(customer_data_csv), id_column="customer_id")
        sink = FileSink(str(output_file))
        pipeline = DataPipeline(source, sink, num_threads=1)
        
        pipeline.run()
        pipeline.cleanup()
        
        # Verify email format in output
        with open(output_file, 'r') as f:
            for line in f:
                record = json.loads(line)
                content = json.loads(record["content"])
                email = content["email"]
                assert "@" in email
                assert "." in email.split("@")[1]
    
    def test_vip_customer_identification(self, customer_data_csv, tmp_path):
        """Verify VIP customers are correctly identified"""
        output_file = tmp_path / "customers_output.jsonl"
        
        source = CSVSource(str(customer_data_csv), id_column="customer_id")
        sink = FileSink(str(output_file))
        pipeline = DataPipeline(source, sink, num_threads=1)
        
        pipeline.run()
        pipeline.cleanup()
        
        # Find VIP customer
        vip_found = False
        with open(output_file, 'r') as f:
            for line in f:
                record = json.loads(line)
                content = json.loads(record["content"])
                if content["status"] == "vip":
                    vip_found = True
                    assert float(content["balance"]) > 10000.00
        
        assert vip_found, "VIP customer not found in output"


class TestTransactionDataMigration:
    """Tests specific to transaction data migration scenarios"""
    
    def test_transaction_chronology(self, transaction_data_csv, tmp_path):
        """Verify transactions maintain chronological order"""
        output_file = tmp_path / "transactions_output.jsonl"
        
        source = CSVSource(str(transaction_data_csv), id_column="txn_id")
        sink = FileSink(str(output_file))
        pipeline = DataPipeline(source, sink, num_threads=1)
        
        pipeline.run()
        pipeline.cleanup()
        
        # Read transactions and verify order
        transactions = []
        with open(output_file, 'r') as f:
            for line in f:
                record = json.loads(line)
                content = json.loads(record["content"])
                transactions.append(content["timestamp"])
        
        # Verify they're in chronological order (assuming CSV is ordered)
        assert transactions == sorted(transactions)
    
    def test_refund_transactions_present(self, transaction_data_csv, tmp_path):
        """Verify refund transactions are not lost during migration"""
        output_file = tmp_path / "transactions_output.jsonl"
        
        source = CSVSource(str(transaction_data_csv), id_column="txn_id")
        sink = FileSink(str(output_file))
        pipeline = DataPipeline(source, sink, num_threads=1)
        
        pipeline.run()
        pipeline.cleanup()
        
        # Count refund transactions
        refund_count = 0
        with open(output_file, 'r') as f:
            for line in f:
                record = json.loads(line)
                content = json.loads(record["content"])
                if content["type"] == "refund":
                    refund_count += 1
        
        assert refund_count > 0, "No refund transactions found"


# ============================================================================
# Data Quality Tests
# ============================================================================

class TestDataQuality:
    """Tests to verify data quality during migration"""
    
    def test_no_empty_records(self, customer_data_csv, tmp_path):
        """Verify no records have empty critical fields"""
        output_file = tmp_path / "quality_check_output.jsonl"
        
        source = CSVSource(str(customer_data_csv), id_column="customer_id")
        sink = FileSink(str(output_file))
        pipeline = DataPipeline(source, sink, num_threads=1)
        
        pipeline.run()
        pipeline.cleanup()
        
        critical_fields = ["customer_id", "name", "email"]
        
        with open(output_file, 'r') as f:
            for line in f:
                record = json.loads(line)
                content = json.loads(record["content"])
                
                for field in critical_fields:
                    assert field in content
                    assert content[field]  # Not empty
                    assert content[field].strip()  # Not just whitespace
    
    def test_numeric_fields_valid(self, customer_data_csv, tmp_path):
        """Verify numeric fields have valid values"""
        output_file = tmp_path / "numeric_check_output.jsonl"
        
        source = CSVSource(str(customer_data_csv), id_column="customer_id")
        sink = FileSink(str(output_file))
        pipeline = DataPipeline(source, sink, num_threads=1)
        
        pipeline.run()
        pipeline.cleanup()
        
        with open(output_file, 'r') as f:
            for line in f:
                record = json.loads(line)
                content = json.loads(record["content"])
                
                # Balance should be a valid number
                balance = float(content["balance"])
                assert balance >= 0  # Can't have negative balance
    
    def test_id_format_consistency(self, customer_data_csv, tmp_path):
        """Verify ID format consistency"""
        output_file = tmp_path / "id_format_output.jsonl"
        
        source = CSVSource(str(customer_data_csv), id_column="customer_id")
        sink = FileSink(str(output_file))
        pipeline = DataPipeline(source, sink, num_threads=1)
        
        pipeline.run()
        pipeline.cleanup()
        
        with open(output_file, 'r') as f:
            for line in f:
                record = json.loads(line)
                customer_id = record["id"]
                
                # All customer IDs should start with 'C'
                assert customer_id.startswith("C")
                # Should be in format CXXX
                assert len(customer_id) == 4


# ============================================================================
# Performance Tests
# ============================================================================

class TestPerformance:
    """Performance-related tests"""
    
    def test_large_dataset_migration(self, tmp_path):
        """Test migration of larger dataset"""
        # Generate large CSV
        large_csv = tmp_path / "large_dataset.csv"
        num_records = 10000
        
        with open(large_csv, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=["id", "data"])
            writer.writeheader()
            for i in range(num_records):
                writer.writerow({"id": str(i), "data": f"record_{i}"})
        
        output_file = tmp_path / "large_output.jsonl"
        
        source = CSVSource(str(large_csv))
        sink = FileSink(str(output_file))
        pipeline = DataPipeline(source, sink, num_threads=1)
        
        import time
        start = time.time()
        stats = pipeline.run()
        duration = time.time() - start
        
        pipeline.cleanup()
        
        # Verify all records processed
        assert stats["inserted"] == num_records
        
        # Should complete in reasonable time (adjust threshold as needed)
        assert duration < 10, f"Migration took {duration}s, expected < 10s"
        
        # Verify output file size is reasonable
        file_size = os.path.getsize(output_file)
        assert file_size > 0


# ============================================================================
# Run Custom Tests
# ============================================================================

if __name__ == "__main__":
    """
    Run these custom tests:
    
    pytest custom_tests.py -v
    pytest custom_tests.py::TestCustomerDataMigration -v
    pytest custom_tests.py -k "vip" -v
    """
    pytest.main([__file__, "-v"])
