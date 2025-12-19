# Contributing to Elasticsearch to MySQL Data Pipeline

Thank you for your interest in contributing! This project welcomes contributions from the community.

## 🤝 How to Contribute

### Reporting Bugs

If you find a bug, please open an issue with:
- A clear description of the problem
- Steps to reproduce
- Expected vs actual behavior
- Your environment (Python version, OS, etc.)

### Suggesting Features

Feature suggestions are welcome! Please open an issue describing:
- The problem you're trying to solve
- Your proposed solution
- Any alternatives you've considered

### Submitting Pull Requests

1. **Fork the repository**
2. **Create a feature branch**: `git checkout -b feature/my-new-feature`
3. **Make your changes**
4. **Add tests** for any new functionality
5. **Ensure all tests pass**: `pytest test_pipeline.py -v`
6. **Commit with clear messages**: `git commit -m "Add feature: description"`
7. **Push to your fork**: `git push origin feature/my-new-feature`
8. **Open a Pull Request**

## 🧪 Testing

All contributions must include tests. Run the test suite:

```bash
# Install dependencies
pip install -r requirements.txt

# Run tests
pytest test_pipeline.py -v

# Check coverage
pytest test_pipeline.py --cov=. --cov-report=html
```

## 📝 Code Style

- Follow PEP 8 style guidelines
- Use meaningful variable names
- Add docstrings to classes and functions
- Keep functions focused and single-purpose

## 🏗️ Adding New Data Sources or Sinks

To add a new data source:

1. Create a class that inherits from `DataSource` in `data_interfaces.py`
2. Implement all abstract methods
3. Add it to the appropriate implementation file or create a new one
4. Update `pipeline_cli.py` to support it
5. Add tests in `test_pipeline.py` or create new test file
6. Update documentation

Example:
```python
from data_interfaces import DataSource

class MyNewSource(DataSource):
    def fetch_records(self, query_params=None):
        # Your implementation
        yield (record_id, content)
    
    def close(self):
        # Cleanup
        pass
```

## 📚 Documentation

- Update README.md if you add new features
- Add examples to the relevant documentation files
- Ensure all public methods have docstrings

## 🎯 Areas We'd Love Help With

- Additional data source implementations (MongoDB, PostgreSQL, Kafka, etc.)
- Additional data sink implementations (S3, GCS, Azure, etc.)
- Performance optimizations
- More comprehensive test coverage
- Documentation improvements
- Example use cases

## ✅ Checklist Before Submitting PR

- [ ] Tests pass locally
- [ ] New tests added for new functionality
- [ ] Documentation updated
- [ ] Code follows PEP 8 style
- [ ] Commit messages are clear
- [ ] No sensitive information in commits

## 🙏 Recognition

Contributors will be acknowledged in the README. Thank you for making this project better!

## 📧 Questions?

If you have questions, feel free to:
- Open an issue
- Email: kevin_mcallorum@linux.com

## 📄 License

By contributing, you agree that your contributions will be licensed under the MIT License.
