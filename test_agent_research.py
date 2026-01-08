"""
Agent research tests using pytest-agents for AI-powered schema validation

These tests use AI agents to analyze ES mappings, validate schema compatibility,
and detect potential issues in the data pipeline.

NOTE: These tests require pytest-agents TypeScript agents to be built.
Run 'make install' in a pytest-agents project to build the agents.
Without built agents, these tests will be skipped.

Author: Kevin McAllorum (kevin_mcallorum@linux.com)
GitHub: github.com/kmcallorum
License: MIT
"""
import pytest
import json
import os

# Skip all tests if pytest-agents not available
pytest_agents = pytest.importorskip("pytest_agents")


def safe_invoke_agent(agent, agent_name, action, params):
    """Safely invoke agent, skipping test if agent not built"""
    try:
        return agent.invoke_agent(agent_name, action, params)
    except RuntimeError as e:
        if "not found" in str(e) or "Run 'make install'" in str(e):
            pytest.skip(f"Agent not built: {e}")
        raise


@pytest.mark.agent_research
class TestSchemaValidation:
    """AI-powered schema validation tests"""

    def test_validate_es_mapping_against_mysql_schema(self, agent):
        """AI validates that ES mapping fields can map to MySQL columns"""
        schema_path = os.path.join(os.path.dirname(__file__), "schemas", "example_scans.json")

        if not os.path.exists(schema_path):
            pytest.skip("Schema file not found")

        with open(schema_path) as f:
            schema = json.load(f)

        result = safe_invoke_agent(agent, 'research', 'analyze_document', {
            'content': json.dumps(schema, indent=2),
            'prompt': 'Analyze this ES schema and identify any fields that might have MySQL type mapping issues'
        })

        assert 'errors' not in result.get('issues', [])

    def test_detect_nested_field_complexity(self, agent):
        """AI detects deeply nested fields that may need flattening for MySQL"""
        schema_path = os.path.join(os.path.dirname(__file__), "schemas", "example_scans.json")

        if not os.path.exists(schema_path):
            pytest.skip("Schema file not found")

        with open(schema_path) as f:
            schema = json.load(f)

        result = safe_invoke_agent(agent, 'research', 'analyze_document', {
            'content': json.dumps(schema.get('sample_document', {}), indent=2),
            'prompt': 'Identify nested objects that would need flattening for a relational database'
        })

        assert result is not None

    def test_validate_field_naming_conventions(self, agent):
        """AI validates field names follow consistent conventions"""
        schema_path = os.path.join(os.path.dirname(__file__), "schemas", "example_scans.json")

        if not os.path.exists(schema_path):
            pytest.skip("Schema file not found")

        with open(schema_path) as f:
            schema = json.load(f)

        result = safe_invoke_agent(agent, 'research', 'analyze_document', {
            'content': json.dumps(schema.get('sample_document', {}), indent=2),
            'prompt': 'Check if field names use consistent naming conventions (camelCase vs snake_case)'
        })

        assert result is not None


@pytest.mark.agent_research
@pytest.mark.slow
class TestDataQualityAnalysis:
    """AI-powered data quality analysis"""

    def test_identify_nullable_fields(self, agent):
        """AI identifies fields that might contain null values"""
        sample_data = {
            "id": "123",
            "name": "Test",
            "optional_field": None,
            "nested": {
                "value": 100,
                "maybe_null": None
            }
        }

        result = safe_invoke_agent(agent, 'research', 'analyze_document', {
            'content': json.dumps(sample_data, indent=2),
            'prompt': 'Identify all fields that contain null values or might be nullable'
        })

        assert result is not None

    def test_detect_potential_data_type_issues(self, agent):
        """AI detects fields with inconsistent or problematic data types"""
        sample_records = [
            {"id": "1", "value": "100", "timestamp": "2024-01-01"},
            {"id": "2", "value": 200, "timestamp": 1704067200},
            {"id": "3", "value": "300.5", "timestamp": "2024-01-03T00:00:00Z"}
        ]

        result = safe_invoke_agent(agent, 'research', 'analyze_document', {
            'content': json.dumps(sample_records, indent=2),
            'prompt': 'Identify fields with inconsistent data types across records'
        })

        assert result is not None
