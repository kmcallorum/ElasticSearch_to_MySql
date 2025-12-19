# Elasticsearch Data Pipeline with Dependency Injection

[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Tests](https://github.com/kmcallorum/ElasticSearch_to_MySql/actions/workflows/tests.yml/badge.svg)](https://github.com/kmcallorum/ElasticSearch_to_MySql/actions/workflows/tests.yml)
[![Tests](https://img.shields.io/badge/tests-pytest-green.svg)](https://docs.pytest.org/)

A production-ready, testable data migration tool for moving data between Elasticsearch, MySQL, CSV files, and other sources/sinks. Built with dependency injection for maximum flexibility and testability.

> **Built by a Principal Engineer with 43 years of enterprise software experience**, including work at Bell Labs (DSL technology) and Bank of New York (stock market systems) on critical infrastructure achieving 99.9% uptime.

## Why This Exists

Traditional data migration scripts are monolithic and hard to test. This project solves that by using dependency injection to separate concerns, making it easy to test migrations with CSV files before running against production databases.

## Architecture

The codebase uses **dependency injection** to separate concerns and enable testing:

```
┌─────────────────┐
│  DataSource     │ (Abstract Interface)
├─────────────────┤
│ - fetch_records │
│ - close         │
└─────────────────┘
        ▲
        │ implements
        │
┌───────┴──────────────────────────┐
│                                  │
│  ElasticsearchSource    CSVSource│
│  (Production)           (Test)   │
└──────────────────────────────────┘

┌─────────────────┐
│  DataSink       │ (Abstract Interface)
├─────────────────┤
│ - insert_record │
│ - commit        │
│ - close         │
│ - get_stats     │
└─────────────────┘
        ▲
        │ implements
        │
┌───────┴────────────────────────────────┐
│                                        │
│  MySQLSink    FileSink    JSONLSink   │
│  (Production)  (Test)      (Test)     │
└────────────────────────────────────────┘

┌─────────────────┐
│  DataPipeline   │
├─────────────────┤
│ - run()         │
│ - cleanup()     │
└─────────────────┘
```

## File Structure

- **`data_interfaces.py`** - Abstract base classes (DataSource, DataSink)
- **`production_impl.py`** - Production implementations (Elasticsearch, MySQL)
- **`test_impl.py`** - Test implementations (CSV, File, JSONL)
- **`pipeline.py`** - Core pipeline logic with threading support
- **`pipeline_cli.py`** - CLI entry point with dependency injection
- **`test_pipeline.py`** - Pytest test suite

## Usage Examples

### Production: Elasticsearch → MySQL

```bash
python pipeline_cli.py \
  --source_type elasticsearch \
  --sink_type mysql \
  --es_url "http://localhost:9200/myindex/_search" \
  --es_user "elastic" \
  --es_pass "password" \
  --db_host "localhost" \
  --db_user "root" \
  --db_pass "password" \
  --db_name "mydb" \
  --db_table "mytable" \
  --threads 5 \
  --gte "2024-01-01T00:00:00" \
  --lte "2024-01-31T23:59:59"
```

### Testing: CSV → File

```bash
python pipeline_cli.py \
  --source_type csv \
  --sink_type file \
  --csv_file "test_data.csv" \
  --output_file "output.jsonl" \
  --threads 1 \
  --limit 100
```

### Testing: CSV → JSONL

```bash
python pipeline_cli.py \
  --source_type csv \
  --sink_type jsonl \
  --csv_file "sample.csv" \
  --csv_id_column "record_id" \
  --csv_content_column "json_data" \
  --output_file "results.jsonl" \
  --threads 1
```

## Running Tests

```bash
# Install pytest if needed
pip install pytest

# Run all tests
pytest test_pipeline.py -v

# Run specific test class
pytest test_pipeline.py::TestDuplicateHandling -v

# Run with coverage
pip install pytest-cov
pytest test_pipeline.py --cov=. --cov-report=html
```

## Creating Test Data

```python
# create_test_data.py
import csv

with open('test_data.csv', 'w', newline='') as f:
    writer = csv.DictWriter(f, fieldnames=["id", "name", "value"])
    writer.writeheader()
    for i in range(1, 1001):
        writer.writerow({"id": str(i), "name": f"User{i}", "value": str(i*100)})
```

## Extending the System

### Add a New Data Source

```python
# custom_source.py
from data_interfaces import DataSource
from typing import Iterator, Tuple, Optional, Dict, Any

class CustomSource(DataSource):
    def __init__(self, connection_string: str):
        self.connection_string = connection_string
        # Initialize your source
    
    def fetch_records(self, query_params: Optional[Dict[str, Any]] = None) -> Iterator[Tuple[str, str]]:
        # Fetch from your source
        for record_id, content in self._fetch():
            yield (record_id, content)
    
    def close(self):
        # Cleanup
        pass
```

### Add a New Data Sink

```python
# custom_sink.py
from data_interfaces import DataSink
from typing import Dict

class CustomSink(DataSink):
    def __init__(self, config: dict):
        self.config = config
        self.stats = {"inserted": 0, "skipped": 0, "errors": 0}
    
    def insert_record(self, record_id: str, content: str) -> bool:
        # Insert logic here
        self.stats["inserted"] += 1
        return True
    
    def commit(self):
        # Commit transaction
        pass
    
    def close(self):
        # Cleanup
        pass
    
    def get_stats(self) -> Dict[str, int]:
        return self.stats.copy()
```

## Thread Safety

- **MySQL Sink**: Thread-safe, use `--threads 5` or higher
- **File Sinks**: Not thread-safe, always use `--threads 1`
- **Pipeline**: Automatically handles single vs multi-threaded execution

## Benefits of This Architecture

1. **Testability**: Test without external dependencies (ES, MySQL)
2. **Flexibility**: Swap implementations without changing core logic
3. **Maintainability**: Clear separation of concerns
4. **Regression Testing**: Automated tests catch breaking changes
5. **Reusability**: Add new sources/sinks by implementing interfaces

## Logging

All operations are logged to:
- `pipeline.log` (file)
- `stdout` (console)

Log levels can be adjusted in the CLI files.

## Migration from Original Script

The original `es_to_mysql.py` has been refactored into modular components. To use the new system with your existing workflow:

**Old way:**
```bash
python es_to_mysql.py --es_url ... --db_host ... --db_table ...
```

**New way (identical functionality):**
```bash
python pipeline_cli.py --source_type elasticsearch --sink_type mysql \
  --es_url ... --db_host ... --db_table ... --threads 5
```

## Requirements

```
requests
mysql-connector-python
pytest (for testing)
pytest-cov (optional, for coverage)
```

Install with:
```bash
pip install requests mysql-connector-python pytest pytest-cov
```

## Performance Considerations

- **Batch Size**: Adjust `--batch_size` for ES (default: 1000)
- **Threads**: Use 5-10 threads for MySQL, 1 for files
- **Memory**: Large batches use more memory but fewer API calls
- **Network**: Multi-threading helps with network-bound operations

## Troubleshooting

**Q: Tests fail with "No module named 'data_interfaces'"**  
A: Ensure you're running tests from the directory containing all Python files.

**Q: MySQL connection fails in tests**  
A: Tests use file-based implementations, no MySQL needed.

**Q: Duplicate records in output**  
A: Check that your ID column is correctly specified with `--csv_id_column`.

**Q: Empty output file**  
A: Check logs for errors, verify CSV file exists and has headers.

## 📄 License

MIT License - See [LICENSE](LICENSE) file for details.

Copyright (c) 2024 Mac McAllorum

## 👤 Author

**Mac McAllorum**
- Email: kevin_mcallorum@linux.com
- GitHub: [@kmcallorum](https://github.com/kmcallorum)
- Experience: 43 years in enterprise software engineering
  - Bell Labs: DSL technology development
  - Bank of New York: Stock market systems
  - Current: Principal Engineer at UHG/Optum

## 🙏 Credits

Refactored from original ES-to-MySQL migration script with focus on testability, maintainability, extensibility, and following software engineering best practices.
