# ⚡ QUICK FIX - Removed Broken Test

## Problem:
```python
test_cli_logger_debug_call() - FAILED
```

The test tried to patch `logger.debug` AFTER the module import, but the logger.debug call happens DURING import. Can't patch retroactively.

---

## Fix:
Removed the redundant test. The first test `test_cli_import_error_path()` already covers lines 32-34.

---

## Run Again:
```bash
pytest --cov=. --cov-report=html

# Then check specific files
pytest --cov=pipeline --cov=pipeline_cli --cov=metrics_server \
       --cov-report=term-missing
```

---

## Check Coverage:
After running, check if we hit 100% or if we still have missing lines!

If still not 100%, run:
```bash
pytest --cov=pipeline --cov=pipeline_cli --cov=metrics_server \
       --cov-report=term-missing
```

And paste the output!
