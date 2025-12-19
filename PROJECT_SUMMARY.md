# Elasticsearch Data Pipeline with Dependency Injection

[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Tests](https://img.shields.io/badge/tests-pytest-green.svg)](https://docs.pytest.org/)

**Author:** Kevin McAllorum (kevin_mcallorum@linux.com)  
**GitHub:** [github.com/kmcallorum](https://github.com/kmcallorum)

> Built by a Principal Engineer with 43 years of enterprise software experience, including work at Bell Labs (DSL technology) and Bank of New York (stock market systems) on critical infrastructure achieving 99.9% uptime.

---

## 🎯 Project Summary

This project refactors a monolithic Elasticsearch-to-MySQL data migration script into a modern, testable architecture using **dependency injection**. The new design enables:

- ✅ **Testing without external dependencies** (use CSV files instead of ES/MySQL)
- ✅ **Automated regression testing** with pytest
- ✅ **Flexible source/sink combinations** (mix and match implementations)
- ✅ **Easy extension** (add new data sources or sinks without modifying core code)

## 📁 Project Structure

```
.
├── data_interfaces.py           # Abstract base classes (DataSource, DataSink)
├── production_impl.py           # Production: Elasticsearch + MySQL
├── test_impl.py                 # Testing: CSV + File/JSONL
├── pipeline.py                  # Core pipeline orchestration
├── pipeline_cli.py              # CLI entry point
│
├── test_pipeline.py             # Automated test suite (pytest)
├── custom_tests_example.py      # Example domain-specific tests
│
├── generate_test_data.py        # Utility to create test CSV files
├── custom_implementations.py    # Examples: REST, PostgreSQL, S3, MongoDB, Kafka
│
├── README.md                    # Main documentation
├── MIGRATION_GUIDE.md           # Old vs New comparison
├── requirements.txt             # Python dependencies
└── quickstart.sh                # Quick start demo script
```

## 🚀 Quick Start

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Run the Demo
```bash
./quickstart.sh
```

This will:
- Generate test data
- Run the pipeline (CSV → JSONL)
- Show results
- Run automated tests

### 3. Run Production Migration
```bash
python pipeline_cli.py \
  --source_type elasticsearch \
  --sink_type mysql \
  --es_url "http://localhost:9200/index/_search" \
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

## 🧪 Testing

### Run All Tests
```bash
pytest test_pipeline.py -v
```

### Run Specific Test Class
```bash
pytest test_pipeline.py::TestDuplicateHandling -v
```

### Run with Coverage
```bash
pytest test_pipeline.py --cov=. --cov-report=html
open htmlcov/index.html
```

### Create Custom Tests
See `custom_tests_example.py` for examples of domain-specific tests.

## 🏗️ Architecture

### The Dependency Injection Pattern

```python
# Define interfaces
class DataSource(ABC):
    @abstractmethod
    def fetch_records(self) -> Iterator[Tuple[str, str]]:
        pass

class DataSink(ABC):
    @abstractmethod
    def insert_record(self, record_id: str, content: str) -> bool:
        pass

# Implement for production
class ElasticsearchSource(DataSource):
    def fetch_records(self):
        # ES-specific implementation
        pass

class MySQLSink(DataSink):
    def insert_record(self, record_id, content):
        # MySQL-specific implementation
        pass

# Implement for testing
class CSVSource(DataSource):
    def fetch_records(self):
        # Read from CSV - no ES needed!
        pass

class FileSink(DataSink):
    def insert_record(self, record_id, content):
        # Write to file - no MySQL needed!
        pass

# Pipeline accepts any implementation
class DataPipeline:
    def __init__(self, source: DataSource, sink: DataSink):
        self.source = source
        self.sink = sink
    
    def run(self):
        for record_id, content in self.source.fetch_records():
            self.sink.insert_record(record_id, content)

# Production: ES → MySQL
pipeline = DataPipeline(
    ElasticsearchSource(...),
    MySQLSink(...)
)

# Testing: CSV → File
pipeline = DataPipeline(
    CSVSource("test.csv"),
    FileSink("output.jsonl")
)
```

## 📊 Key Benefits

| Feature | Before (Monolithic) | After (DI) |
|---------|-------------------|-----------|
| Testing | ❌ Requires ES + MySQL | ✅ CSV + File |
| Test Speed | ❌ Minutes | ✅ Seconds |
| Flexibility | ❌ One hardcoded path | ✅ Mix any source/sink |
| Extensibility | ❌ Modify main script | ✅ Add new classes |
| Regression Tests | ❌ Not possible | ✅ Automated suite |
| Maintenance | ❌ Tightly coupled | ✅ Separated concerns |

## 🔧 Extending the System

### Add a New Data Source

```python
from data_interfaces import DataSource

class MyCustomSource(DataSource):
    def __init__(self, config):
        # Initialize your source
        pass
    
    def fetch_records(self, query_params=None):
        # Implement fetching logic
        for record_id, content in self._fetch():
            yield (record_id, content)
    
    def close(self):
        # Cleanup
        pass
```

### Add a New Data Sink

```python
from data_interfaces import DataSink

class MyCustomSink(DataSink):
    def __init__(self, config):
        self.stats = {"inserted": 0, "skipped": 0, "errors": 0}
    
    def insert_record(self, record_id, content):
        # Implement insertion logic
        self.stats["inserted"] += 1
        return True
    
    def commit(self):
        pass
    
    def close(self):
        pass
    
    def get_stats(self):
        return self.stats.copy()
```

See `custom_implementations.py` for complete examples of:
- REST API Source
- PostgreSQL Source
- S3 Sink
- MongoDB Sink
- Kafka Sink

## 📝 Example Use Cases

### 1. Test Migration Logic Before Production
```bash
# Test with small CSV first
python pipeline_cli.py \
  --source_type csv \
  --sink_type file \
  --csv_file test_data_small.csv \
  --output_file output.jsonl \
  --threads 1

# Verify output, then run production
```

### 2. Debug ES Issues Without MySQL
```bash
# Export ES data to file for inspection
python pipeline_cli.py \
  --source_type elasticsearch \
  --sink_type jsonl \
  --es_url "..." \
  --output_file "es_debug.jsonl" \
  --threads 1 \
  --limit 100
```

### 3. Load CSV Test Data into MySQL
```bash
# Use CSV as source for MySQL testing
python pipeline_cli.py \
  --source_type csv \
  --sink_type mysql \
  --csv_file sample_data.csv \
  --db_host localhost \
  --db_user root \
  --db_pass password \
  --db_name testdb \
  --db_table test_results \
  --threads 5
```

### 4. Automated Regression Testing
```bash
# Every code change automatically tested
pytest test_pipeline.py -v

# Catches breaking changes before production
```

## 🎓 Key Concepts

### Dependency Injection
- Components depend on **interfaces**, not concrete implementations
- Implementations are "injected" at runtime
- Enables easy swapping of components for testing

### Abstract Base Classes
- Define the contract that implementations must follow
- Ensure all implementations have consistent APIs
- Enable polymorphism (treating different implementations the same)

### Test Doubles
- CSVSource and FileSink are "test doubles" (mock implementations)
- Allow testing without external dependencies
- Much faster and more reliable than integration tests

## 🐛 Troubleshooting

### "No module named 'data_interfaces'"
Run from the directory containing all Python files.

### MySQL Connection Errors in Tests
Tests don't need MySQL - they use file-based implementations.

### Empty Output File
Check `pipeline.log` for errors. Verify input file exists and has correct format.

### Slow Tests
Reduce test data size with `--limit` parameter.

## 📈 Performance

- **Batch Size**: Adjust `--batch_size` (default: 1000)
- **Threading**: Use 5-10 threads for MySQL, always 1 for files
- **Memory**: Larger batches = more memory, fewer API calls

## 🔐 Thread Safety

- **MySQL Sink**: Thread-safe, use multiple threads
- **File Sinks**: Not thread-safe, use `--threads 1`
- Pipeline automatically handles single vs multi-threaded execution

## 📚 Further Reading

- **README.md** - Main documentation and usage
- **MIGRATION_GUIDE.md** - Detailed comparison of old vs new
- **custom_implementations.py** - Examples for REST, S3, MongoDB, etc.
- **custom_tests_example.py** - How to write domain-specific tests

## ✨ What Makes This Special

1. **Production-Ready**: Maintains all original functionality
2. **Test-Friendly**: Comprehensive automated test suite
3. **Extensible**: Easy to add new sources/sinks
4. **Well-Documented**: Clear examples and migration guide
5. **Best Practices**: Follows SOLID principles, dependency injection pattern

## 🤝 Contributing

To add a new data source or sink:
1. Implement the appropriate interface (DataSource or DataSink)
2. Add tests to verify behavior
3. Update CLI to support new implementation
4. Document usage in README

## 📄 License

MIT License - See [LICENSE](LICENSE) file for details.

Copyright (c) 2024 Kevin McAllorum

## 🙏 Credits

Refactored from original ES-to-MySQL migration script with focus on:
- Testability
- Maintainability
- Extensibility
- Following software engineering best practices

---

**Ready to get started?** Run `./quickstart.sh` to see it in action!
