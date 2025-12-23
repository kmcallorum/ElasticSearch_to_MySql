# Start MySQL
docker run --name test-mysql \
  -e MYSQL_ROOT_PASSWORD=test123 \
  -e MYSQL_DATABASE=testdb \
  -p 3306:3306 \
  -d mysql:8

sleep 20

# Create table with WRONG name
docker exec test-mysql mysql -uroot -ptest123 testdb -e "
CREATE TABLE wrong_table_name (
    id VARCHAR(255) PRIMARY KEY,
    content JSON NOT NULL
);"

# Run pipeline pointing to 'scans' (doesn't exist!)
python pipeline_cli.py \
  --source_type jsonl \
  --jsonl_file test_data_example_scans.jsonl \
  --sink_type mysql \
  --db_host 127.0.0.1 \
  --db_user root \
  --db_pass test123 \
  --db_name testdb \
  --db_table scans \
  --threads 1 \
  --ai-errors
