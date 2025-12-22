#!/bin/bash
set -e

LOGFILE="daily_run.log"

{
  echo "----- $(date '+%Y-%m-%d %H:%M:%S') START -----"
  #!/bin/bash
  set -e

  # Load environment variables from a .env file if present
  if [ -f .env ]; then
    source .env
  fi

  source .venv/bin/activate
  cd /es-to-mysql-cli
  python migrate.py \
    --es_url "$ES_URL" \
    --api_key "$API_KEY" \
    --db_host "$DB_HOST" \
    --db_user "$DB_USER" \
    --db_pass "$DB_PASS" \
    --db_name "$DB_NAME" \
    --db_table "$DB_TABLE" \
    --gte "$(python3 -c 'from datetime import datetime, timedelta; print((datetime.utcnow() - timedelta(hours=25)).strftime("%Y-%m-%dT%H:00:00"))')" \
    --lte "$(python3 -c 'from datetime import datetime, timedelta; print((datetime.utcnow() - timedelta(hours=1)).strftime("%Y-%m-%dT%H:59:59"))')" \
    --threads 10 \
    --batch_size 2000
  EXIT_CODE=$?
  echo "Exit code: $EXIT_CODE"
  echo "----- $(date '+%Y-%m-%d %H:%M:%S') END -----"
} >> "$LOGFILE" 2>&1