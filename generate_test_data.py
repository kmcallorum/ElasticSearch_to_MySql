"""
Generate test CSV files for testing the pipeline
"""
import csv
import json
import random
from datetime import datetime, timedelta


def generate_simple_csv(filename, num_records=100):
    """Generate a simple CSV file with basic fields"""
    print(f"Generating {filename} with {num_records} records...")
    
    with open(filename, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=["id", "name", "value", "timestamp"])
        writer.writeheader()
        
        for i in range(1, num_records + 1):
            writer.writerow({
                "id": str(i),
                "name": f"User_{i}",
                "value": str(random.randint(100, 10000)),
                "timestamp": (datetime.now() - timedelta(days=random.randint(0, 365))).isoformat()
            })
    
    print(f"Created {filename}")


def generate_json_content_csv(filename, num_records=100):
    """Generate CSV with JSON content in a column"""
    print(f"Generating {filename} with {num_records} JSON records...")
    
    with open(filename, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=["id", "content"])
        writer.writeheader()
        
        for i in range(1, num_records + 1):
            content = {
                "user_id": i,
                "username": f"user{i}",
                "email": f"user{i}@example.com",
                "balance": random.uniform(100, 10000),
                "status": random.choice(["active", "inactive", "suspended"]),
                "created_at": (datetime.now() - timedelta(days=random.randint(0, 365))).isoformat()
            }
            writer.writerow({
                "id": str(i),
                "content": json.dumps(content)
            })
    
    print(f"Created {filename}")


def generate_csv_with_duplicates(filename, num_records=50, duplicate_rate=0.2):
    """Generate CSV with some duplicate IDs"""
    print(f"Generating {filename} with duplicates...")
    
    records = []
    
    # Generate unique records
    for i in range(1, num_records + 1):
        records.append({
            "id": str(i),
            "data": f"original_{i}",
            "timestamp": datetime.now().isoformat()
        })
    
    # Add duplicates
    num_duplicates = int(num_records * duplicate_rate)
    for _ in range(num_duplicates):
        dup_id = str(random.randint(1, num_records))
        records.append({
            "id": dup_id,
            "data": f"duplicate_{dup_id}",
            "timestamp": datetime.now().isoformat()
        })
    
    # Write shuffled records
    random.shuffle(records)
    
    with open(filename, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=["id", "data", "timestamp"])
        writer.writeheader()
        writer.writerows(records)
    
    print(f"Created {filename} with {num_duplicates} duplicates")


def generate_large_csv(filename, num_records=10000):
    """Generate a large CSV for performance testing"""
    print(f"Generating large file {filename} with {num_records} records...")
    
    with open(filename, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=["id", "category", "amount", "description"])
        writer.writeheader()
        
        categories = ["electronics", "books", "clothing", "food", "sports"]
        
        for i in range(1, num_records + 1):
            writer.writerow({
                "id": f"REC{i:06d}",
                "category": random.choice(categories),
                "amount": f"{random.uniform(10, 5000):.2f}",
                "description": f"Transaction {i} - {random.choice(['purchase', 'refund', 'exchange'])}"
            })
            
            if i % 1000 == 0:
                print(f"  ...{i} records written")
    
    print(f"Created {filename}")


if __name__ == "__main__":
    # Generate various test files
    generate_simple_csv("test_data_small.csv", num_records=10)
    generate_simple_csv("test_data_medium.csv", num_records=100)
    generate_json_content_csv("test_json_data.csv", num_records=50)
    generate_csv_with_duplicates("test_duplicates.csv", num_records=100, duplicate_rate=0.2)
    generate_large_csv("test_data_large.csv", num_records=10000)
    
    print("\nAll test files generated successfully!")
    print("\nUsage examples:")
    print("  python pipeline_cli.py --source_type csv --sink_type file \\")
    print("    --csv_file test_data_small.csv --output_file output.jsonl --threads 1")
    print("\n  python pipeline_cli.py --source_type csv --sink_type jsonl \\")
    print("    --csv_file test_json_data.csv --output_file output.jsonl --threads 1")
