#!/bin/bash
set -e

LOGFILE="daily_run_ai_error_test.log"

# Cleanup function to remove container
cleanup() {
echo "Cleaning up ..."
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

# Run pipeline pointing to 'scans' (doesn't exist - should trigger AI error detection)
echo "Running pipeline with --ai-errors flag..."
python pipeline_cli.py \
--source_type elasticsearch \
--es_url ${ES_URL} \
--api_key ${API_KEY} \
--sink_type mysql \
--db_host ${DB_HOST} \
--db_user ${DB_USER} \
--db_pass ${DB_PASS} \
--db_table ${DB_TABLE} \
--db_name ${DB_NAME} \
--threads 1 \
--gte "$(python3 -c 'from datetime import datetime, timedelta; print((datetime.utcnow() - timedelta(hours=109)).strftime("%Y-%m-%dT%H:00:00"))')" \
--lte "$(python3 -c 'from datetime import datetime, timedelta; print((datetime.utcnow() - timedelta(hours=13)).strftime("%Y-%m-%dT%H:59:59"))')" \
--ai-errors

EXIT_CODE=$?
echo "Exit code: $EXIT_CODE"
echo "----- $(date '+%Y-%m-%d %H:%M:%S') END -----"
} >> "$LOGFILE" 2>&1

# Display the last few lines of the log
echo "Test complete. Last 20 lines of log:"
tail -20 "$LOGFILE"
