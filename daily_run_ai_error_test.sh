#!/bin/bash
set -e

LOGFILE="daily_run_ai_error_test.log"

# Cleanup function to remove container
cleanup() {
  echo "Cleaning up test-mysql container..."
  docker stop test-mysql 2>/dev/null || true
  docker rm test-mysql 2>/dev/null || true
}

# Set trap to cleanup on exit
trap cleanup EXIT

{
  echo "----- $(date '+%Y-%m-%d %H:%M:%S') START -----"

  # Load environment variables from a .env file if present
  if [ -f .env ]; then
    echo "Loading environment variables from .env"
    source .env
  fi

  # Activate virtual environment
  if [ -f .venv/bin/activate ]; then
    echo "Activating virtual environment"
    source .venv/bin/activate
  fi

  # Clean up any existing test container
  cleanup

  # Start MySQL container
  echo "Starting MySQL container..."
  docker run --name test-mysql \
    -e MYSQL_ROOT_PASSWORD=${DB_TEST_PASSWORD:-test123} \
    -e MYSQL_DATABASE=testdb \
    -p 3306:3306 \
    -d mysql:8

  # Wait for MySQL to be ready
  echo "Waiting for MySQL to be ready..."
  sleep 20

  # Create table with WRONG name (intentional mismatch for AI error detection)
  echo "Creating table with wrong name (wrong_table_name instead of scans)..."
  docker exec test-mysql mysql -uroot -p${DB_TEST_PASSWORD:-test123} testdb -e "
  CREATE TABLE wrong_table_name (
      id VARCHAR(255) PRIMARY KEY,
      content JSON NOT NULL
  );"

  # Run pipeline pointing to 'scans' (doesn't exist - should trigger AI error detection)
  echo "Running pipeline with --ai-errors flag..."
  python pipeline_cli.py \
    --source_type jsonl \
    --jsonl_file test_data_example_scans.jsonl \
    --sink_type mysql \
    --db_host 127.0.0.1 \
    --db_user root \
    --db_pass ${DB_TEST_PASSWORD:-test123} \
    --db_table scans \
    --db_name testdb \
    --threads 1 \
    --ai-errors

  EXIT_CODE=$?
  echo "Exit code: $EXIT_CODE"
  echo "----- $(date '+%Y-%m-%d %H:%M:%S') END -----"
} >> "$LOGFILE" 2>&1

# Display the last few lines of the log
echo "Test complete. Last 20 lines of log:"
tail -20 "$LOGFILE"
