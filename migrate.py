import argparse
import requests
import json
import mysql.connector
import logging
import threading
from queue import Queue
import sys

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("es_to_mysql.log"),
        logging.StreamHandler(sys.stdout)
    ]
)

def mysql_connection(host, user, password, database):
    return mysql.connector.connect(host=host, user=user, password=password, database=database)

def insert_worker(queue, db_config, table):
    conn = mysql_connection(**db_config)
    cursor = conn.cursor()
    # Use INSERT IGNORE to skip duplicates automatically without errors
    insert_sql = f"INSERT IGNORE INTO {table} (id, content) VALUES (%s, %s)"
    inserted_count = 0
    skipped_count = 0
    total_processed = 0

    while True:
        item = queue.get()
        if item is None:
            break
        row_id, content_json = item
        try:
            cursor.execute(insert_sql, (row_id, content_json))
            if cursor.rowcount > 0:
                inserted_count += 1
            else:
                skipped_count += 1
        except Exception as e:
            logging.error(f"Error inserting ID {row_id}: {e}")
        total_processed += 1
        if total_processed % 100 == 0:
            logging.info(f"Worker progress: {total_processed} processed, {inserted_count} inserted, {skipped_count} skipped")
        queue.task_done()

    conn.commit()
    logging.info(f"Worker finished: {total_processed} processed, {inserted_count} inserted, {skipped_count} duplicates skipped")
    cursor.close()
    conn.close()

def main():
    parser = argparse.ArgumentParser(description="Fetch data from Elasticsearch and insert into MySQL with pagination and threading.")
    
    # Elasticsearch args
    parser.add_argument("--es_url", required=True, help="Elasticsearch URL (e.g., http://host:9200/index/_search)")
    parser.add_argument("--es_user", help="Elasticsearch username (for basic auth)")
    parser.add_argument("--es_pass", help="Elasticsearch password (for basic auth)")
    parser.add_argument("--api_key", help="Elasticsearch API Key (alternative to user/pass)")
    
    # MySQL args
    parser.add_argument("--db_host", required=True)
    parser.add_argument("--db_user", required=True)
    parser.add_argument("--db_pass", required=True)
    parser.add_argument("--db_name", required=True)
    parser.add_argument("--db_table", required=True)
    
    # Query options
    parser.add_argument("--gte", help="Start date (e.g., 2020-06-01T00:00:00)")
    parser.add_argument("--lte", help="End date (e.g., 2020-06-30T23:59:59)")
    parser.add_argument("--match_all", action="store_true", help="Use match_all query instead of range")
    parser.add_argument("--threads", type=int, default=5, help="Number of threads for DB inserts")
    parser.add_argument("--batch_size", type=int, default=1000, help="Batch size for Elasticsearch scroll")
    
    args = parser.parse_args()

    # Validate authentication
    if not args.api_key and (not args.es_user or not args.es_pass):
        logging.error("Error: Either --api_key or both --es_user and --es_pass must be provided.")
        sys.exit(1)

    # Build query
    if args.match_all:
        query = {"query": {"match_all": {}}}
    else:
        if not args.gte or not args.lte:
            logging.error("Error: --gte and --lte required unless --match_all is used.")
            sys.exit(1)
        query = {
            "query": {
                "range": {
                    "@timestamp": {
                        "gte": args.gte,
                        "lte": args.lte,
                        "format": "strict_date_optional_time"
                    }
                }
            }
        }

    # MySQL config
    db_config = {
        "host": args.db_host,
        "user": args.db_user,
        "password": args.db_pass,
        "database": args.db_name
    }

    # Initialize queue and threads
    queue = Queue()
    threads = []
    logging.info(f"Starting {args.threads} insert worker threads for table {args.db_table} in DB {args.db_name} on host {args.db_host} as user {args.db_user}")
    for i in range(args.threads):
        t = threading.Thread(target=insert_worker, args=(queue, db_config, args.db_table), name=f"InsertWorker-{i+1}")
        t.start()
        threads.append(t)

    # Elasticsearch scroll
    scroll_url = args.es_url
    headers = {"Content-Type": "application/json"}
    params = {"scroll": "2m", "size": args.batch_size}
    
    # Setup authentication
    auth = None
    if args.api_key:
        headers["Authorization"] = f"ApiKey {args.api_key}"
    else:
        auth = (args.es_user, args.es_pass)

    logging.info("Starting Elasticsearch scroll...")
    response = requests.post(scroll_url, auth=auth, headers=headers, params=params, data=json.dumps(query))
    if response.status_code != 200:
        logging.error(f"Initial scroll request failed: {response.status_code}, {response.text}")
        sys.exit(1)

    data = response.json()
    scroll_id = data.get("_scroll_id")
    hits = data.get("hits", {}).get("hits", [])
    total_inserted = 0

    while hits:
        for hit in hits:
            row_id = hit["_id"]
            content_json = json.dumps(hit)
            queue.put((row_id, content_json))
        total_inserted += len(hits)
        logging.info(f"Queued {len(hits)} records. Total so far: {total_inserted}")

        # Get next batch
        # Extract base ES URL (remove /index/_search part)
        base_url = args.es_url.split('/_search')[0].rsplit('/', 1)[0]
        response = requests.post(f"{base_url}/_search/scroll", auth=auth,
                                 headers=headers, data=json.dumps({"scroll": "2m", "scroll_id": scroll_id}))
        if response.status_code != 200:
            logging.error(f"Scroll request failed: {response.status_code}, {response.text}")
            break
        data = response.json()
        scroll_id = data.get("_scroll_id")
        hits = data.get("hits", {}).get("hits", [])

    # Stop workers
    queue.join()
    for _ in threads:
        queue.put(None)
    for t in threads:
        t.join()

    logging.info(f"Completed. Total records processed from Elasticsearch: {total_inserted}")
    logging.info("If the MySQL table is still empty, check the worker logs above for inserted/skipped counts and verify DB connection parameters.")

if __name__ == "__main__":
    main()
