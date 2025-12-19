# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2024-12-19

### Added
- Initial release with dependency injection architecture
- ElasticsearchSource and MySQLSink for production use
- CSVSource and FileSink/JSONLSink for testing
- Comprehensive pytest test suite with 8+ test classes
- Multi-threaded pipeline support
- CLI with pluggable source/sink selection
- Complete documentation (README, MIGRATION_GUIDE, PROJECT_SUMMARY)
- Example custom implementations (REST, PostgreSQL, S3, MongoDB, Kafka)
- Test data generator utility
- MIT License
- GitHub Actions for automated testing
- Contributing guidelines

### Features
- Abstract DataSource and DataSink interfaces
- Production-ready Elasticsearch to MySQL migration
- Test with CSV files without external dependencies
- Duplicate detection and handling
- Statistics tracking (inserted, skipped, errors)
- Configurable batch sizes and threading
- Query parameter support for filtering
- Extensive logging
- Error handling and recovery

### Documentation
- README with usage examples
- PROJECT_SUMMARY with architecture overview
- MIGRATION_GUIDE comparing old vs new approach
- Custom implementation examples
- Custom test examples
- Quickstart script for demos

## [Unreleased]

### Planned
- PostgreSQL source implementation
- S3 sink implementation
- MongoDB sink implementation
- Performance benchmarking suite
- Docker support
- Schema validation
- Data transformation pipeline
- Incremental migration support
