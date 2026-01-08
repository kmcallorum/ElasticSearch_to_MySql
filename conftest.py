"""
Pytest configuration and shared fixtures for ES-MySQL pipeline tests

Author: Kevin McAllorum (kevin_mcallorum@linux.com)
GitHub: github.com/kmcallorum
License: MIT
"""
import pytest
import tempfile
import csv
import json
import os


# =============================================================================
# COMMON FIXTURES
# =============================================================================

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
        for i in range(1, 6):
            writer.writerow({
                "id": str(i),
                "name": f"User{i}",
                "value": str(i * 100),
                "timestamp": f"2024-01-0{i}"
            })

    return csv_path


@pytest.fixture
def sample_jsonl_file(temp_dir):
    """Create a sample JSONL file for testing"""
    jsonl_path = os.path.join(temp_dir, "test_data.jsonl")

    with open(jsonl_path, 'w') as f:
        for i in range(1, 6):
            record = {"id": str(i), "name": f"User{i}", "value": i * 100}
            f.write(json.dumps(record) + "\n")

    return jsonl_path


@pytest.fixture
def large_csv_file(temp_dir):
    """Create a larger CSV file for performance tests"""
    csv_path = os.path.join(temp_dir, "large_data.csv")

    with open(csv_path, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=["id", "data", "value"])
        writer.writeheader()
        for i in range(1000):
            writer.writerow({
                "id": str(i),
                "data": f"test_data_{i}",
                "value": str(i * 10)
            })

    return csv_path


# =============================================================================
# PYTEST-AGENTS FIXTURES
# =============================================================================

@pytest.fixture
def agent(request):
    """Fixture providing access to pytest-agents bridge"""
    bridge = getattr(request.config, "_pytest_agents_bridge", None)
    if bridge is None:
        pytest.skip("pytest-agents bridge not available")

    # Check if research agent is actually available (built)
    if not bridge.is_agent_available("research"):
        pytest.skip("research agent not built - run 'make install' to build agents")

    return bridge


# =============================================================================
# MARKER-BASED SKIPPING
# =============================================================================

def pytest_configure(config):
    """Register custom markers"""
    config.addinivalue_line("markers", "unit: Unit tests")
    config.addinivalue_line("markers", "integration: Integration tests")
    config.addinivalue_line("markers", "performance: Performance benchmarks")
    config.addinivalue_line("markers", "agent_research: AI agent tests")
    config.addinivalue_line("markers", "slow: Long-running tests")
    config.addinivalue_line("markers", "multithreaded: Multi-threaded tests")


def pytest_collection_modifyitems(config, items):
    """Skip integration tests if no ES/MySQL available"""
    skip_integration = pytest.mark.skip(reason="Integration environment not available")

    for item in items:
        if "integration" in item.keywords:
            # Check for ES/MySQL environment vars
            if not os.environ.get("MYSQL_HOST") and not os.environ.get("ES_HOST"):
                item.add_marker(skip_integration)
