# Migration Guide: Old vs New Architecture

## Overview

This guide shows the differences between the original monolithic script and the new dependency injection architecture.

## Architecture Comparison

### Old Approach (Monolithic)

```
┌────────────────────────────────────────┐
│                                        │
│         es_to_mysql.py                 │
│                                        │
│  ┌──────────────────────────────────┐  │
│  │ • Elasticsearch connection       │  │
│  │ • MySQL connection               │  │
│  │ • Threading logic                │  │
│  │ • Query building                 │  │
│  │ • Error handling                 │  │
│  │ • Logging                        │  │
│  └──────────────────────────────────┘  │
│                                        │
└────────────────────────────────────────┘

Issues:
- Hard to test (requires ES + MySQL)
- Tightly coupled components
- Can't reuse with different sources/sinks
- No regression testing capability
```

### New Approach (Dependency Injection)

```
┌─────────────────────────────────────────────────┐
│              Interfaces                         │
│  ┌──────────────┐         ┌──────────────┐     │
│  │ DataSource   │         │  DataSink    │     │
│  └──────────────┘         └──────────────┘     │
└─────────────────────────────────────────────────┘
           ▲                        ▲
           │                        │
           │ implements             │ implements
           │                        │
┌──────────┴──────────┐    ┌───────┴─────────────┐
│  Production         │    │  Production         │
│  - ESSource         │    │  - MySQLSink        │
│  - PostgreSQL       │    │  - MongoDB          │
└─────────────────────┘    └─────────────────────┘
           ▲                        ▲
           │                        │
           │ also implements        │ also implements
           │                        │
┌──────────┴──────────┐    ┌───────┴─────────────┐
│  Test               │    │  Test               │
│  - CSVSource        │    │  - FileSink         │
│  - MockSource       │    │  - MockSink         │
└─────────────────────┘    └─────────────────────┘
           ▲                        ▲
           │                        │
           └────────────┬───────────┘
                        │
                 ┌──────┴───────┐
                 │  Pipeline    │
                 │  (Orchestr.) │
                 └──────────────┘

Benefits:
✓ Easy to test (use CSV/File implementations)
✓ Loosely coupled (swap implementations)
✓ Reusable (add new sources/sinks easily)
✓ Regression testing enabled
```

## Code Comparison

### Before: Monolithic Script

```python
# Everything in one file, tightly coupled

def main():
    # Parse args
    parser = argparse.ArgumentParser()
    parser.add_argument("--es_url", required=True)
    parser.add_argument("--db_host", required=True)
    # ... many more args
    
    args = parser.parse_args()
    
    # Build ES query (hardcoded logic)
    if args.match_all:
        query = {"query": {"match_all": {}}}
    else:
        query = {
            "query": {
                "range": {
                    "@timestamp": {
                        "gte": args.gte,
                        "lte": args.lte
                    }
                }
            }
        }
    
    # ES scroll (hardcoded, can't test without ES)
    response = requests.post(scroll_url, auth=auth, ...)
    # ... more ES-specific code
    
    # MySQL insert (hardcoded, can't test without MySQL)
    conn = mysql.connector.connect(host=args.db_host, ...)
    cursor.execute(insert_sql, (row_id, content_json))
    # ... more MySQL-specific code

# Problems:
# - Can't test without ES and MySQL running
# - Can't reuse with different data sources
# - Changes risk breaking entire script
# - No way to run regression tests
```

### After: Dependency Injection

```python
# Separated concerns, testable, extensible

# 1. Define interfaces (data_interfaces.py)
class DataSource(ABC):
    @abstractmethod
    def fetch_records(self, query_params) -> Iterator[Tuple[str, str]]:
        pass

class DataSink(ABC):
    @abstractmethod
    def insert_record(self, record_id: str, content: str) -> bool:
        pass

# 2. Implement production versions (production_impl.py)
class ElasticsearchSource(DataSource):
    def fetch_records(self, query_params):
        # ES-specific implementation
        pass

class MySQLSink(DataSink):
    def insert_record(self, record_id, content):
        # MySQL-specific implementation
        pass

# 3. Implement test versions (test_impl.py)
class CSVSource(DataSource):
    def fetch_records(self, query_params):
        # Read from CSV - no ES needed!
        pass

class FileSink(DataSink):
    def insert_record(self, record_id, content):
        # Write to file - no MySQL needed!
        pass

# 4. Pipeline orchestrates (pipeline.py)
class DataPipeline:
    def __init__(self, source: DataSource, sink: DataSink):
        self.source = source
        self.sink = sink
    
    def run(self):
        for record_id, content in self.source.fetch_records():
            self.sink.insert_record(record_id, content)

# 5. Use it (pipeline_cli.py or tests)
# Production:
pipeline = DataPipeline(
    ElasticsearchSource(...),
    MySQLSink(...)
)

# Testing:
pipeline = DataPipeline(
    CSVSource("test.csv"),
    FileSink("output.txt")
)

# Benefits:
# ✓ Can test without external dependencies
# ✓ Can swap implementations easily
# ✓ Changes to one component don't break others
# ✓ Automated regression testing possible
```

## Testing Comparison

### Before: No Automated Tests

```bash
# Manual testing only:
# 1. Start Elasticsearch
# 2. Start MySQL
# 3. Load test data into ES
# 4. Run script
# 5. Manually verify MySQL contents
# 6. Clean up databases

# Problems:
# - Slow (minutes per test)
# - Error-prone (manual verification)
# - Expensive (need running services)
# - No regression testing
```

### After: Automated Test Suite

```bash
# Automated pytest tests:
pytest test_pipeline.py -v

# Tests run in seconds
# No external dependencies needed
# Automated verification
# Regression tests on every commit

# Example test:
def test_duplicate_handling(sample_csv_with_duplicates, temp_dir):
    source = CSVSource(sample_csv_with_duplicates)
    sink = FileSink(os.path.join(temp_dir, "output.jsonl"))
    pipeline = DataPipeline(source, sink)
    
    stats = pipeline.run()
    
    assert stats["inserted"] == 3  # Only unique records
    assert stats["skipped"] == 2   # Duplicates skipped
```

## Usage Comparison

### Production Use (Identical Functionality)

```bash
# OLD WAY
python es_to_mysql.py \
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

# NEW WAY (same result, more flexible)
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

### New Capabilities

```bash
# Test with CSV instead of ES
python pipeline_cli.py \
  --source_type csv \
  --sink_type file \
  --csv_file test_data.csv \
  --output_file output.jsonl \
  --threads 1

# Can mix and match: CSV → MySQL
python pipeline_cli.py \
  --source_type csv \
  --sink_type mysql \
  --csv_file data.csv \
  --db_host localhost \
  --db_user root \
  --db_pass password \
  --db_name testdb \
  --db_table results \
  --threads 5

# Can mix and match: ES → File (for inspection)
python pipeline_cli.py \
  --source_type elasticsearch \
  --sink_type jsonl \
  --es_url "..." \
  --es_user "..." \
  --es_pass "..." \
  --output_file "es_export.jsonl" \
  --threads 1
```

## Extension Comparison

### Adding New Source (Old Way)

```python
# Would require modifying the main script
# Risk breaking existing functionality
# Hard to test in isolation

def main():
    # ... existing ES code ...
    
    # Now you want to add PostgreSQL?
    # Need to add new args, new logic, new connections
    # Everything intertwined, hard to maintain
```

### Adding New Source (New Way)

```python
# custom_source.py
from data_interfaces import DataSource

class PostgreSQLSource(DataSource):
    def __init__(self, connection_string):
        self.conn = psycopg2.connect(connection_string)
    
    def fetch_records(self, query_params):
        # PostgreSQL-specific implementation
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM mytable")
        for row in cursor:
            yield (row[0], json.dumps(row))

# Use it immediately with existing pipeline:
from pipeline import DataPipeline
from production_impl import MySQLSink

pipeline = DataPipeline(
    PostgreSQLSource("postgres://..."),
    MySQLSink(...)
)
pipeline.run()

# No changes to existing code!
# Fully testable in isolation!
```

## Transition Strategy

### Phase 1: Run Both in Parallel
- Keep old script for production
- Use new architecture for testing
- Build confidence with new system

### Phase 2: Switch to New System
- Move production to new pipeline
- Keep old script as backup
- Monitor for issues

### Phase 3: Deprecate Old Script
- Remove old script
- Full regression test suite
- Document new architecture

## Key Takeaways

| Aspect | Old (Monolithic) | New (DI) |
|--------|-----------------|----------|
| **Testability** | ❌ Requires ES+MySQL | ✅ CSV+File for tests |
| **Flexibility** | ❌ Hardcoded sources | ✅ Pluggable implementations |
| **Maintainability** | ❌ Tightly coupled | ✅ Separated concerns |
| **Extensibility** | ❌ Modify main script | ✅ Add new classes |
| **Test Speed** | ❌ Minutes | ✅ Seconds |
| **Regression Tests** | ❌ Not possible | ✅ Automated suite |
| **Learning Curve** | ✅ Simple to start | ⚠️ More files to understand |
| **Production Use** | ✅ Works fine | ✅ Identical functionality |

## Conclusion

The new architecture provides:
1. **Same production functionality** - no loss of features
2. **Better testing** - fast, automated, no dependencies
3. **More flexibility** - easy to add new sources/sinks
4. **Better maintenance** - separated concerns, easier to modify
5. **Confidence** - regression tests catch breaking changes

The trade-off is slightly more complexity (more files), but this is offset by much better long-term maintainability and testing capabilities.
