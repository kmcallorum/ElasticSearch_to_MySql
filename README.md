# Elasticsearch to MySQL Converter

A Python CLI tool that dynamically converts Elasticsearch JSON exports into normalized MySQL relational tables. Automatically discovers schema from your data, handles nested objects, arrays, and creates proper foreign key relationships.

## Features

- **Auto-Schema Discovery** - Scans sample documents to infer table structures
- **Dynamic Table Creation** - Creates tables based on discovered schema
- **Nested Object Handling** - Converts nested JSON objects to child tables with FK relationships
- **Array Support**
  - Arrays of objects → child tables (one row per array item)
  - Arrays of primitives → junction tables + master lookup tables
- **Reserved Name Handling** - Automatically prefixes reserved column names (`id`, `parent_id`, etc.)
- **Idempotent Loading** - Safe to re-run without duplicating data
- **Flexible Configuration** - Skip paths, keep fields as JSON blobs, control batch sizes
- **CLI-Driven** - Full command-line interface with multiple operation modes

## Requirements

```bash
pip install mysql-connector-python
```

## Installation

```bash
git clone https://github.com/optum-eeps/ElasticSearch_to_MySql.git
cd ElasticSearch_to_MySql
```

## Quick Start

### 1. Prepare Your Data

First, load your Elasticsearch JSON export into a MySQL staging table:

```sql
CREATE TABLE your_staging_table (
    id VARCHAR(255),
    content JSON
);

-- Load your ES export (adjust path as needed)
-- id is Elasticsearch's document ID (retained for reference/testing)
-- content holds the JSON document data
LOAD DATA LOCAL INFILE '/path/to/es_export.json'
INTO TABLE your_staging_table
LINES TERMINATED BY '\n'
(content);
```

### 2. Discover Schema

```bash
python flatten_es_data_to_mysql.py -H localhost -u root -p mypassword -d mydb -t your_staging_table --discover-only
```

### 3. Create Tables and Load Data

```bash
python flatten_es_data_to_mysql.py -H localhost -u root -p mypassword -d mydb -t your_staging_table
```

## Usage

### Basic Usage

```bash
python flatten_es_data_to_mysql.py -H localhost -u root -p mypassword -d mydb -t your_staging_table
```

### Command Line Options

| Option | Short | Description | Default |
|--------|-------|-------------|---------|
| `--host` | `-H` | MySQL host (required) | - |
| `--port` | `-P` | MySQL port | 3306 |
| `--user` | `-u` | MySQL user (required) | - |
| `--password` | `-p` | MySQL password (required) | - |
| `--database` | `-d` | MySQL database (required) | - |
| `--temp-table` | `-t` | Source staging table name (required) | - |
| `--json-column` | `-j` | Column name containing JSON data | `content` |
| `--sample` | - | Sample size for schema discovery | 100 |
| `--batch` | - | Batch size for commits | 100 |
| `--skip` | - | JSON paths to skip (space-separated) | - |
| `--keep-json` | - | Paths to store as JSON blob | - |
| `--discover-only` | - | Only discover schema, no changes | - |
| `--create-only` | - | Create tables but don't load data | - |

### Examples

```bash
# Discover schema only (no database changes)
python flatten_es_data_to_mysql.py -H localhost -u root -p secret -d mydb -t es_export --discover-only

# Create tables but don't load data yet
python flatten_es_data_to_mysql.py -H localhost -u root -p secret -d mydb -t es_export --create-only

# Full run
python flatten_es_data_to_mysql.py -H localhost -u root -p secret -d mydb -t es_export

# Skip noisy paths and increase sample size
python flatten_es_data_to_mysql.py -H localhost -u root -p secret -d mydb \
    -t es_export \
    --skip event.original metadata.debug \
    --sample 500

# Keep complex nested data as JSON blob
python flatten_es_data_to_mysql.py -H localhost -u root -p secret -d mydb \
    -t es_export \
    --keep-json eventData.rawPayload

# Large batch processing
python flatten_es_data_to_mysql.py -H localhost -u root -p secret -d mydb \
    -t es_export \
    --sample 500 \
    --batch 500
```

## How It Works

### Schema Discovery

The tool scans a sample of documents and builds a schema by:

1. Identifying scalar fields → columns on parent table
2. Detecting nested objects → separate child tables with `parent_id` FK
3. Detecting arrays of objects → child tables (multiple rows per parent)
4. Detecting arrays of primitives → junction tables + master lookup tables

### Table Naming Convention

| JSON Path | Table Name |
|-----------|------------|
| (root) | `document` |
| `eventData` | `document_eventdata` |
| `pipelineData` | `document_pipelinedata` |
| `pipelineData.pipelineLibraries` | `document_pipelinedata_pipelinelibraries` |

### Column Naming

- Spaces and special characters are converted to underscores
- All names are lowercased
- Reserved names (`id`, `parent_id`, `_id`, `_index`, `_version`) are prefixed with table context

Example: A field named `id` in table `document_pipelinedata_pipelinelibraries` becomes `pipelinelibraries_id`.

## Data Structure Mapping

### Input: Elasticsearch Document

```json
{
  "_index": "my-index",
  "_id": "abc123",
  "_version": 1,
  "_source": {
    "@version": "1",
    "@timestamp": "2024-01-15T10:30:00Z",
    "eventData": {
      "type": "build",
      "status": "success",
      "duration_ms": 45000
    },
    "pipelineData": {
      "pipelineId": "pipeline-001",
      "gitUrl": "https://github.com/org/repo",
      "askId": ["UHGWM110-019726", "UHGWM110-019727"],
      "pipelineLibraries": [
        {"id": "com.example.library", "version": "v1.0.0"},
        {"id": "com.example.utils", "version": "v2.1.0"}
      ]
    },
    "testData": {
      "totalTests": 150,
      "testsPassed": 148,
      "testsFailed": 2
    }
  }
}
```

### Output: MySQL Tables

```
document
├── id (PK, AUTO_INCREMENT)
├── src_id (from _id)
├── src_index (from _index)
├── src_version (from _version)
├── version (from @version)
└── timestamp (from @timestamp)

document_eventdata
├── id (PK)
├── parent_id (FK → document.id)
├── type
├── status
└── duration_ms

document_pipelinedata
├── id (PK)
├── parent_id (FK → document.id)
├── pipelineid
└── giturl

document_testdata
├── id (PK)
├── parent_id (FK → document.id)
├── totaltests
├── testspassed
└── testsfailed

document_pipelinedata_pipelinelibraries
├── id (PK)
├── parent_id (FK → document_pipelinedata.id)
├── pipelinelibraries_id (renamed from "id")
└── version

askid_master
├── id (PK)
└── value (UNIQUE) -- "UHGWM110-019726", etc.

document_pipelinedata_askid (junction)
├── id (PK)
├── parent_id (FK → document_pipelinedata.id)
└── master_id (FK → askid_master.id)
```

## Array Handling

### Arrays of Objects

Arrays containing objects become child tables with one row per array element:

```json
"pipelineLibraries": [
  {"id": "lib1", "version": "v1.0"},
  {"id": "lib2", "version": "v2.0"}
]
```

Creates `document_pipelinedata_pipelinelibraries` with 2 rows, both pointing to the same `parent_id`.

### Arrays of Primitives

Arrays containing scalar values create a junction table + master lookup table:

```json
"askId": ["ASK001", "ASK002"]
```

Creates:
- `askid_master` - unique values with auto-increment IDs
- `document_pipelinedata_askid` - junction linking parent to master IDs

This approach:
- Normalizes repeated values (no string duplication)
- Enables efficient querying ("find all documents with ASK001")
- Maintains referential integrity

## Schema Discovery Output

Running with `--discover-only` produces output like:

```
============================================================
SCHEMA DISCOVERY
============================================================
Sampled documents for schema discovery
Document tables: 4
Master tables:   1
Junction tables: 1
============================================================

DOCUMENT TABLES:
  document
    path: /
    parent: ROOT
    columns: 4 (src_id, src_index, src_version, version, timestamp)
  document_eventdata
    path: eventData
    parent: document
    columns: 3 (type, status, duration_ms)
  document_pipelinedata
    path: pipelineData
    parent: document
    columns: 2 (pipelineid, giturl)
  document_pipelinedata_pipelinelibraries
    path: pipelineData.pipelineLibraries
    parent: document_pipelinedata
    columns: 2 (pipelinelibraries_id, version)

MASTER TABLES:
  askid_master
    source: pipelineData.askId

JUNCTION TABLES:
  document_pipelinedata_askid -> askid_master

Discovery complete. Exiting (--discover-only)
```

## Configuration Tips

### Skipping Redundant Paths

If your ES data has redundant nested structures (like `event.original` containing a copy of the whole document), skip them:

```bash
--skip event.original
```

### Keeping Complex Data as JSON

For fields with highly variable structure that don't need relational querying:

```bash
--keep-json eventData.rawPayload metadata.custom
```

### Sample Size

Increase sample size if your documents have varying structures:

```bash
--sample 500
```

The tool discovers columns across all sampled documents, so a larger sample catches more edge cases.

### Batch Size

For large datasets, adjust batch size for performance:

```bash
--batch 500
```

Larger batches = fewer commits = faster loading, but more memory usage.

## Querying the Results

### Find all documents with a specific askId

```sql
SELECT d.*
FROM document d
JOIN document_pipelinedata pd ON pd.parent_id = d.id
JOIN document_pipelinedata_askid ja ON ja.parent_id = pd.id
JOIN askid_master am ON am.id = ja.master_id
WHERE am.value = 'UHGWM110-019726';
```

### Get document with all related data

```sql
SELECT 
    d.src_id as es_id,
    d.timestamp,
    ed.type as event_type,
    ed.status,
    pd.pipelineid,
    pd.giturl,
    td.totaltests,
    td.testspassed
FROM document d
LEFT JOIN document_eventdata ed ON ed.parent_id = d.id
LEFT JOIN document_pipelinedata pd ON pd.parent_id = d.id
LEFT JOIN document_testdata td ON td.parent_id = d.id
WHERE d.id = 1;
```

### List all pipeline libraries used

```sql
SELECT DISTINCT pipelinelibraries_id, version
FROM document_pipelinedata_pipelinelibraries
ORDER BY pipelinelibraries_id;
```

### Count documents by event status

```sql
SELECT ed.status, COUNT(*) as count
FROM document_eventdata ed
GROUP BY ed.status;
```

## Limitations

- **No Foreign Key Constraints** - Tables use `parent_id` columns but don't enforce FK constraints (for flexibility during loading)
- **No Indexes** - You'll want to add indexes after loading for query performance
- **Single-Threaded** - Processing is sequential; large datasets may take time
- **Memory** - Master table caches are held in memory during loading

## Post-Load Optimization

After loading, consider adding indexes:

```sql
-- Document lookups
ALTER TABLE document ADD INDEX idx_src_id (src_id);

-- Parent relationships
ALTER TABLE document_eventdata ADD INDEX idx_parent (parent_id);
ALTER TABLE document_pipelinedata ADD INDEX idx_parent (parent_id);
ALTER TABLE document_testdata ADD INDEX idx_parent (parent_id);

-- Junction table performance
ALTER TABLE document_pipelinedata_askid ADD INDEX idx_parent (parent_id);
ALTER TABLE document_pipelinedata_askid ADD INDEX idx_master (master_id);

-- Master table lookups
ALTER TABLE askid_master ADD INDEX idx_value (value);
```

## License

MIT

## Contributing

Kevin McAllorum, Principal Engineer, TLCP
