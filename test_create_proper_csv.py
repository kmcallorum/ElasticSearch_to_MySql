"""
Tests for create_proper_csv.py utility script

Author: Mac McAllorum
"""
import pytest
import os
import csv
import json
import subprocess
import sys
from pathlib import Path


class TestCreateProperCSV:
    """Test the create_proper_csv.py utility script"""
    
    def test_script_runs_successfully(self, tmp_path):
        """Test that the script runs without errors"""
        # Change to temp directory
        original_dir = os.getcwd()
        os.chdir(tmp_path)
        
        try:
            # Run the script
            result = subprocess.run(
                [sys.executable, Path(original_dir) / "create_proper_csv.py"],
                capture_output=True,
                text=True
            )
            
            assert result.returncode == 0
            assert "✅ Created elasticsearch_proper.csv" in result.stdout
        finally:
            os.chdir(original_dir)
    
    def test_csv_file_created(self, tmp_path):
        """Test that the CSV file is created"""
        original_dir = os.getcwd()
        os.chdir(tmp_path)
        
        try:
            subprocess.run(
                [sys.executable, Path(original_dir) / "create_proper_csv.py"],
                capture_output=True
            )
            
            # Check file exists
            assert (tmp_path / "elasticsearch_proper.csv").exists()
        finally:
            os.chdir(original_dir)
    
    def test_csv_has_correct_structure(self, tmp_path):
        """Test that the CSV has correct headers and rows"""
        original_dir = os.getcwd()
        os.chdir(tmp_path)
        
        try:
            subprocess.run(
                [sys.executable, Path(original_dir) / "create_proper_csv.py"],
                capture_output=True
            )
            
            # Read and verify CSV
            with open(tmp_path / "elasticsearch_proper.csv", 'r') as f:
                reader = csv.reader(f)
                rows = list(reader)
                
                # Check headers
                assert rows[0] == ['id', 'content']
                
                # Check 3 data rows
                assert len(rows) == 4  # header + 3 records
        finally:
            os.chdir(original_dir)
    
    def test_csv_content_is_valid_json(self, tmp_path):
        """Test that content column contains valid JSON"""
        original_dir = os.getcwd()
        os.chdir(tmp_path)
        
        try:
            subprocess.run(
                [sys.executable, Path(original_dir) / "create_proper_csv.py"],
                capture_output=True
            )
            
            with open(tmp_path / "elasticsearch_proper.csv", 'r') as f:
                reader = csv.reader(f)
                next(reader)  # Skip header
                
                for row in reader:
                    # Should be able to parse JSON from content column
                    content = json.loads(row[1])
                    assert '@version' in content
                    assert 'eventData' in content
        finally:
            os.chdir(original_dir)
    
    def test_csv_ids_are_correct(self, tmp_path):
        """Test that IDs are written correctly"""
        original_dir = os.getcwd()
        os.chdir(tmp_path)
        
        try:
            subprocess.run(
                [sys.executable, Path(original_dir) / "create_proper_csv.py"],
                capture_output=True
            )
            
            with open(tmp_path / "elasticsearch_proper.csv", 'r') as f:
                reader = csv.reader(f)
                next(reader)  # Skip header
                rows = list(reader)
                
                # Check IDs
                assert rows[0][0] == "____0XYBQ1N8iksWtSLK"
                assert rows[1][0] == "____1ABC456DEF789GH"
                assert rows[2][0] == "____2XYZ789HIJ012KL"
        finally:
            os.chdir(original_dir)
    
    def test_output_messages(self, tmp_path):
        """Test console output messages"""
        original_dir = os.getcwd()
        os.chdir(tmp_path)
        
        try:
            result = subprocess.run(
                [sys.executable, Path(original_dir) / "create_proper_csv.py"],
                capture_output=True,
                text=True
            )
            
            # Check output messages
            assert "✅ Created elasticsearch_proper.csv" in result.stdout
            assert "✅ 3 records" in result.stdout
            assert "First record preview:" in result.stdout
            assert "ID: ____0XYBQ1N8iksWtSLK" in result.stdout
        finally:
            os.chdir(original_dir)
    
    def test_fortify_data_preserved(self, tmp_path):
        """Test that Fortify-specific data is preserved in JSON"""
        original_dir = os.getcwd()
        os.chdir(tmp_path)
        
        try:
            subprocess.run(
                [sys.executable, Path(original_dir) / "create_proper_csv.py"],
                capture_output=True
            )
            
            with open(tmp_path / "elasticsearch_proper.csv", 'r') as f:
                reader = csv.reader(f)
                next(reader)  # Skip header
                first_row = next(reader)
                
                content = json.loads(first_row[1])
                
                # Verify Fortify data
                assert content['fortifyData']['scanType'] == 'full'
                assert 'fortifyIssues' in content['fortifyData']
                assert 'fortifyBuildName' in content['fortifyData']
        finally:
            os.chdir(original_dir)
    
    def test_all_three_records_different(self, tmp_path):
        """Test that all three records have different content"""
        original_dir = os.getcwd()
        os.chdir(tmp_path)
        
        try:
            subprocess.run(
                [sys.executable, Path(original_dir) / "create_proper_csv.py"],
                capture_output=True
            )
            
            with open(tmp_path / "elasticsearch_proper.csv", 'r') as f:
                reader = csv.reader(f)
                next(reader)  # Skip header
                rows = list(reader)
                
                # Parse all records
                records = [json.loads(row[1]) for row in rows]
                
                # Check they have different statuses
                statuses = [r['eventData']['status'] for r in records]
                assert 'success' in statuses
                assert 'failure' in statuses
                
                # Check they have different timestamps
                timestamps = [r['eventData']['timestamp_ms'] for r in records]
                assert len(set(timestamps)) == 3  # All different
        finally:
            os.chdir(original_dir)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
