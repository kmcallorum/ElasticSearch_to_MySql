"""
Tests for generate_test_data_schema.py utility script

Author: Mac McAllorum
"""
import pytest
import json
import csv
import subprocess
import sys
from pathlib import Path
from generate_test_data_schema import (
    TestDataGenerator,
    save_as_jsonl,
    save_as_csv,
    list_schemas
)


class TestTestDataGenerator:
    """Test the TestDataGenerator class"""
    
    @pytest.fixture
    def sample_schema_file(self, tmp_path):
        """Create a sample schema file for testing"""
        schema = {
            "name": "test_schema",
            "description": "Test schema",
            "elasticsearch": {
                "index_pattern": "test-*"
            },
            "sample_document": {
                "field1": "value1",
                "nested": {
                    "field2": "value2"
                }
            },
            "variation_rules": {
                "field1": {"type": "constant", "value": "constant_value"},
                "nested.field2": {"type": "random_choice", "values": ["a", "b", "c"]}
            }
        }
        
        schema_file = tmp_path / "test.json"
        with open(schema_file, 'w') as f:
            json.dump(schema, f)
        
        return str(schema_file)
    
    def test_initialization(self, sample_schema_file):
        """Test TestDataGenerator initialization"""
        generator = TestDataGenerator(sample_schema_file)
        
        assert generator.schema is not None
        assert 'sample_document' in generator.schema
        assert generator.sample == {"field1": "value1", "nested": {"field2": "value2"}}
    
    def test_apply_rule_random_int(self, sample_schema_file):
        """Test random_int rule"""
        generator = TestDataGenerator(sample_schema_file)
        rule = {"type": "random_int", "min": 1, "max": 10}
        
        value = generator._apply_rule(rule, 0)
        assert 1 <= value <= 10
        assert isinstance(value, int)
    
    def test_apply_rule_random_float(self, sample_schema_file):
        """Test random_float rule"""
        generator = TestDataGenerator(sample_schema_file)
        rule = {"type": "random_float", "min": 1.0, "max": 10.0}
        
        value = generator._apply_rule(rule, 0)
        assert 1.0 <= value <= 10.0
        assert isinstance(value, float)
    
    def test_apply_rule_increment(self, sample_schema_file):
        """Test increment rule"""
        generator = TestDataGenerator(sample_schema_file)
        rule = {"type": "increment", "start": 100, "step": 10}
        
        assert generator._apply_rule(rule, 0) == 100
        assert generator._apply_rule(rule, 1) == 110
        assert generator._apply_rule(rule, 2) == 120
    
    def test_apply_rule_increment_default_step(self, sample_schema_file):
        """Test increment rule with default step"""
        generator = TestDataGenerator(sample_schema_file)
        rule = {"type": "increment", "start": 50}
        
        assert generator._apply_rule(rule, 0) == 50
        assert generator._apply_rule(rule, 1) == 51
    
    def test_apply_rule_random_choice(self, sample_schema_file):
        """Test random_choice rule"""
        generator = TestDataGenerator(sample_schema_file)
        rule = {"type": "random_choice", "values": ["a", "b", "c"]}
        
        value = generator._apply_rule(rule, 0)
        assert value in ["a", "b", "c"]
    
    def test_apply_rule_random_choice_with_weights(self, sample_schema_file):
        """Test random_choice with weights"""
        generator = TestDataGenerator(sample_schema_file)
        rule = {"type": "random_choice", "values": ["a", "b"], "weights": [0.9, 0.1]}
        
        # Run multiple times to verify it works
        values = [generator._apply_rule(rule, i) for i in range(10)]
        assert all(v in ["a", "b"] for v in values)
    
    def test_apply_rule_random_hex(self, sample_schema_file):
        """Test random_hex rule"""
        generator = TestDataGenerator(sample_schema_file)
        rule = {"type": "random_hex", "length": 8}
        
        value = generator._apply_rule(rule, 0)
        assert len(value) == 8
        assert all(c in '0123456789abcdef' for c in value)
    
    def test_apply_rule_random_string(self, sample_schema_file):
        """Test random_string rule"""
        generator = TestDataGenerator(sample_schema_file)
        rule = {"type": "random_string", "length": 12}
        
        value = generator._apply_rule(rule, 0)
        assert len(value) == 12
        assert value.isalnum()
    
    def test_apply_rule_timestamp_increment(self, sample_schema_file):
        """Test timestamp_increment rule"""
        generator = TestDataGenerator(sample_schema_file)
        rule = {"type": "timestamp_increment", "start": 1000000, "step_ms": 5000}
        
        assert generator._apply_rule(rule, 0) == 1000000
        assert generator._apply_rule(rule, 1) == 1005000
        assert generator._apply_rule(rule, 2) == 1010000
    
    def test_apply_rule_timestamp_increment_default_step(self, sample_schema_file):
        """Test timestamp_increment with default step"""
        generator = TestDataGenerator(sample_schema_file)
        rule = {"type": "timestamp_increment", "start": 2000000}
        
        assert generator._apply_rule(rule, 0) == 2000000
        assert generator._apply_rule(rule, 1) == 2001000
    
    def test_apply_rule_constant(self, sample_schema_file):
        """Test constant rule"""
        generator = TestDataGenerator(sample_schema_file)
        rule = {"type": "constant", "value": "fixed"}
        
        assert generator._apply_rule(rule, 0) == "fixed"
        assert generator._apply_rule(rule, 100) == "fixed"
    
    def test_apply_rule_unknown_type(self, sample_schema_file):
        """Test unknown rule type raises error"""
        generator = TestDataGenerator(sample_schema_file)
        rule = {"type": "unknown_rule"}
        
        with pytest.raises(ValueError, match="Unknown rule type"):
            generator._apply_rule(rule, 0)
    
    def test_set_nested_value_simple(self, sample_schema_file):
        """Test setting simple nested value"""
        generator = TestDataGenerator(sample_schema_file)
        doc = {}
        
        generator._set_nested_value(doc, "field", "value")
        assert doc == {"field": "value"}
    
    def test_set_nested_value_deep(self, sample_schema_file):
        """Test setting deeply nested value"""
        generator = TestDataGenerator(sample_schema_file)
        doc = {}
        
        generator._set_nested_value(doc, "level1.level2.level3", "deep_value")
        assert doc == {"level1": {"level2": {"level3": "deep_value"}}}
    
    def test_set_nested_value_existing_path(self, sample_schema_file):
        """Test setting value in existing path"""
        generator = TestDataGenerator(sample_schema_file)
        doc = {"existing": {"field": "old"}}
        
        generator._set_nested_value(doc, "existing.field", "new")
        assert doc["existing"]["field"] == "new"
    
    def test_generate_record_default_id(self, sample_schema_file):
        """Test generate_record with default ID"""
        generator = TestDataGenerator(sample_schema_file)
        record = generator.generate_record(5)
        
        assert 'id' in record
        assert 'content' in record
        assert record['id'] == "____ES_RECORD_00005"
    
    def test_generate_record_custom_id(self, sample_schema_file):
        """Test generate_record with custom base ID"""
        generator = TestDataGenerator(sample_schema_file)
        record = generator.generate_record(3, base_id="CUSTOM")
        
        assert record['id'] == "CUSTOM_00003"
    
    def test_generate_record_applies_rules(self, sample_schema_file):
        """Test that variation rules are applied"""
        generator = TestDataGenerator(sample_schema_file)
        record = generator.generate_record(0)
        
        # Should have applied constant rule
        assert record['content']['field1'] == "constant_value"
        
        # Should have applied random_choice rule
        assert record['content']['nested']['field2'] in ["a", "b", "c"]
    
    def test_generate_batch(self, sample_schema_file):
        """Test generating multiple records"""
        generator = TestDataGenerator(sample_schema_file)
        records = generator.generate_batch(5)
        
        assert len(records) == 5
        assert all('id' in r and 'content' in r for r in records)
        
        # Check IDs are sequential
        ids = [r['id'] for r in records]
        assert ids == [
            "____ES_RECORD_00000",
            "____ES_RECORD_00001",
            "____ES_RECORD_00002",
            "____ES_RECORD_00003",
            "____ES_RECORD_00004"
        ]
    
    def test_generate_batch_custom_id(self, sample_schema_file):
        """Test generating batch with custom ID"""
        generator = TestDataGenerator(sample_schema_file)
        records = generator.generate_batch(3, base_id="TEST")
        
        ids = [r['id'] for r in records]
        assert ids == ["TEST_00000", "TEST_00001", "TEST_00002"]


class TestSaveFunction:
    """Test save_as_jsonl and save_as_csv functions"""
    
    def test_save_as_jsonl(self, tmp_path):
        """Test saving records as JSONL"""
        records = [
            {"id": "1", "content": {"field": "value1"}},
            {"id": "2", "content": {"field": "value2"}}
        ]
        
        output_file = tmp_path / "test.jsonl"
        save_as_jsonl(records, str(output_file))
        
        # Verify file exists and content
        assert output_file.exists()
        
        with open(output_file) as f:
            lines = f.readlines()
        
        assert len(lines) == 2
        assert json.loads(lines[0]) == records[0]
        assert json.loads(lines[1]) == records[1]
    
    def test_save_as_csv(self, tmp_path):
        """Test saving records as CSV"""
        records = [
            {"id": "1", "content": {"field": "value1"}},
            {"id": "2", "content": {"field": "value2"}}
        ]
        
        output_file = tmp_path / "test.csv"
        save_as_csv(records, str(output_file))
        
        # Verify file exists and content
        assert output_file.exists()
        
        with open(output_file) as f:
            reader = csv.reader(f)
            rows = list(reader)
        
        assert len(rows) == 3  # header + 2 records
        assert rows[0] == ['id', 'content']
        assert rows[1][0] == '1'
        assert json.loads(rows[1][1]) == {"field": "value1"}


class TestListSchemas:
    """Test list_schemas function"""
    
    def test_list_schemas_with_schemas(self, tmp_path, capsys):
        """Test listing schemas when they exist"""
        # Create schemas directory
        schemas_dir = tmp_path / "schemas"
        schemas_dir.mkdir()
        
        # Create a test schema
        schema = {
            "name": "test",
            "description": "Test schema",
            "elasticsearch": {"index_pattern": "test-*"}
        }
        
        with open(schemas_dir / "test.json", 'w') as f:
            json.dump(schema, f)
        
        # Change to temp directory
        import os
        original_dir = os.getcwd()
        os.chdir(tmp_path)
        
        try:
            list_schemas()
            captured = capsys.readouterr()
            
            assert "Available schemas:" in captured.out
            assert "test" in captured.out
            assert "Test schema" in captured.out
            assert "test-*" in captured.out
        finally:
            os.chdir(original_dir)
    
    def test_list_schemas_no_directory(self, tmp_path, capsys):
        """Test listing when no schemas directory"""
        import os
        original_dir = os.getcwd()
        os.chdir(tmp_path)
        
        try:
            list_schemas()
            captured = capsys.readouterr()
            
            assert "No schemas directory found" in captured.out
        finally:
            os.chdir(original_dir)
    
    def test_list_schemas_empty_directory(self, tmp_path, capsys):
        """Test listing when schemas directory is empty"""
        schemas_dir = tmp_path / "schemas"
        schemas_dir.mkdir()
        
        import os
        original_dir = os.getcwd()
        os.chdir(tmp_path)
        
        try:
            list_schemas()
            captured = capsys.readouterr()
            
            assert "No schemas found" in captured.out
        finally:
            os.chdir(original_dir)


class TestMainFunction:
    """Test main() function via command-line"""
    
    @pytest.fixture
    def setup_test_env(self, tmp_path):
        """Setup test environment with schema"""
        # Create schemas directory
        schemas_dir = tmp_path / "schemas"
        schemas_dir.mkdir()
        
        # Create test schema
        schema = {
            "name": "test",
            "description": "Test",
            "sample_document": {"field": "value"},
            "variation_rules": {
                "field": {"type": "constant", "value": "test"}
            }
        }
        
        with open(schemas_dir / "test.json", 'w') as f:
            json.dump(schema, f)
        
        return tmp_path
    
    def test_main_list_flag(self, setup_test_env):
        """Test main with --list flag"""
        import os
        original_dir = os.getcwd()
        os.chdir(setup_test_env)
        
        try:
            result = subprocess.run(
                [sys.executable, Path(original_dir) / "generate_test_data_schema.py", "--list"],
                capture_output=True,
                text=True
            )
            
            assert result.returncode == 0
            assert "Available schemas:" in result.stdout
        finally:
            os.chdir(original_dir)
    
    def test_main_generate_jsonl(self, setup_test_env):
        """Test generating JSONL output"""
        import os
        original_dir = os.getcwd()
        os.chdir(setup_test_env)
        
        try:
            result = subprocess.run(
                [sys.executable, Path(original_dir) / "generate_test_data_schema.py",
                 "--schema", "test", "--count", "5"],
                capture_output=True,
                text=True
            )
            
            assert result.returncode == 0
            assert "Generated 5 records" in result.stdout
            assert (setup_test_env / "test_data_test.jsonl").exists()
        finally:
            os.chdir(original_dir)
    
    def test_main_generate_csv(self, setup_test_env):
        """Test generating CSV output"""
        import os
        original_dir = os.getcwd()
        os.chdir(setup_test_env)
        
        try:
            result = subprocess.run(
                [sys.executable, Path(original_dir) / "generate_test_data_schema.py",
                 "--schema", "test", "--count", "3", "--format", "csv"],
                capture_output=True,
                text=True
            )
            
            assert result.returncode == 0
            assert "Generated 3 records" in result.stdout
            assert (setup_test_env / "test_data_test.csv").exists()
        finally:
            os.chdir(original_dir)
    
    def test_main_custom_output(self, setup_test_env):
        """Test with custom output filename"""
        import os
        original_dir = os.getcwd()
        os.chdir(setup_test_env)
        
        try:
            result = subprocess.run(
                [sys.executable, Path(original_dir) / "generate_test_data_schema.py",
                 "--schema", "test", "--count", "2", "--output", "custom.jsonl"],
                capture_output=True,
                text=True
            )
            
            assert result.returncode == 0
            assert (setup_test_env / "custom.jsonl").exists()
        finally:
            os.chdir(original_dir)
    
    def test_main_custom_base_id(self, setup_test_env):
        """Test with custom base ID"""
        import os
        original_dir = os.getcwd()
        os.chdir(setup_test_env)
        
        try:
            result = subprocess.run(
                [sys.executable, Path(original_dir) / "generate_test_data_schema.py",
                 "--schema", "test", "--count", "2", "--base-id", "CUSTOM"],
                capture_output=True,
                text=True
            )
            
            assert result.returncode == 0
            
            # Check output file contains custom IDs
            with open(setup_test_env / "test_data_test.jsonl") as f:
                first_line = f.readline()
                record = json.loads(first_line)
                assert record['id'].startswith("CUSTOM_")
        finally:
            os.chdir(original_dir)
    
    def test_main_missing_schema_arg(self, setup_test_env):
        """Test error when --schema not provided"""
        import os
        original_dir = os.getcwd()
        os.chdir(setup_test_env)
        
        try:
            result = subprocess.run(
                [sys.executable, Path(original_dir) / "generate_test_data_schema.py"],
                capture_output=True,
                text=True
            )
            
            assert result.returncode != 0
            assert "--schema is required" in result.stderr
        finally:
            os.chdir(original_dir)
    
    def test_main_nonexistent_schema(self, setup_test_env):
        """Test error for nonexistent schema"""
        import os
        original_dir = os.getcwd()
        os.chdir(setup_test_env)
        
        try:
            result = subprocess.run(
                [sys.executable, Path(original_dir) / "generate_test_data_schema.py",
                 "--schema", "nonexistent"],
                capture_output=True,
                text=True
            )
            
            assert "Schema not found" in result.stdout
        finally:
            os.chdir(original_dir)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
