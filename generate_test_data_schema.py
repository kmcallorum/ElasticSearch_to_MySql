#!/usr/bin/env python3
"""
Schema-driven test data generator

Generates test data for any Elasticsearch schema defined in schemas/ directory.

Usage:
    python generate_test_data.py --schema fortify_scans --count 100 --output test_data.jsonl
    python generate_test_data.py --schema jenkins_builds --count 50 --format csv

Author: Mac McAllorum
"""
import json
import csv
import argparse
import random
import string
from pathlib import Path
from typing import Dict, Any, List
from copy import deepcopy


class TestDataGenerator:
    """Generate test data based on schema definition"""
    
    def __init__(self, schema_file: str):
        """Initialize with schema file"""
        with open(schema_file) as f:
            self.schema = json.load(f)
        
        self.sample = self.schema['sample_document']
        self.rules = self.schema.get('variation_rules', {})
        self.counters = {}
    
    def _apply_rule(self, rule: Dict[str, Any], record_num: int) -> Any:
        """Apply a variation rule to generate value"""
        rule_type = rule['type']
        
        if rule_type == 'random_int':
            return random.randint(rule['min'], rule['max'])
        
        elif rule_type == 'random_float':
            return random.uniform(rule['min'], rule['max'])
        
        elif rule_type == 'increment':
            start = rule['start']
            step = rule.get('step', 1)
            return start + (record_num * step)
        
        elif rule_type == 'random_choice':
            values = rule['values']
            weights = rule.get('weights')
            return random.choices(values, weights=weights)[0]
        
        elif rule_type == 'random_hex':
            length = rule['length']
            return ''.join(random.choices('0123456789abcdef', k=length))
        
        elif rule_type == 'random_string':
            length = rule['length']
            chars = string.ascii_letters + string.digits
            return ''.join(random.choices(chars, k=length))
        
        elif rule_type == 'timestamp_increment':
            start = rule['start']
            step_ms = rule.get('step_ms', 1000)
            return start + (record_num * step_ms)
        
        elif rule_type == 'constant':
            return rule['value']
        
        else:
            raise ValueError(f"Unknown rule type: {rule_type}")
    
    def _set_nested_value(self, doc: Dict, path: str, value: Any):
        """Set value in nested dictionary using dot notation"""
        parts = path.split('.')
        current = doc
        
        for part in parts[:-1]:
            if part not in current:
                current[part] = {}
            current = current[part]
        
        current[parts[-1]] = value
    
    def generate_record(self, record_num: int, base_id: str = None) -> Dict[str, Any]:
        """Generate a single record"""
        # Deep copy sample document
        record = deepcopy(self.sample)
        
        # Apply variation rules
        for path, rule in self.rules.items():
            value = self._apply_rule(rule, record_num)
            self._set_nested_value(record, path, value)
        
        # Generate ID
        if base_id:
            doc_id = f"{base_id}_{record_num:05d}"
        else:
            doc_id = f"____ES_RECORD_{record_num:05d}"
        
        return {
            'id': doc_id,
            'content': record
        }
    
    def generate_batch(self, count: int, base_id: str = None) -> List[Dict[str, Any]]:
        """Generate multiple records"""
        return [self.generate_record(i, base_id) for i in range(count)]


def save_as_jsonl(records: List[Dict], output_file: str):
    """Save records as JSONL"""
    with open(output_file, 'w') as f:
        for record in records:
            f.write(json.dumps(record) + '\n')


def save_as_csv(records: List[Dict], output_file: str):
    """Save records as CSV with properly escaped JSON"""
    with open(output_file, 'w', newline='') as f:
        writer = csv.writer(f, quoting=csv.QUOTE_MINIMAL)
        writer.writerow(['id', 'content'])
        
        for record in records:
            # Convert content to JSON string
            content_json = json.dumps(record['content'])
            writer.writerow([record['id'], content_json])


def list_schemas():
    """List available schemas"""
    schema_dir = Path('schemas')
    if not schema_dir.exists():
        print("No schemas directory found")
        return
    
    schemas = list(schema_dir.glob('*.json'))
    if not schemas:
        print("No schemas found in schemas/")
        return
    
    print("\nAvailable schemas:")
    print("=" * 60)
    for schema_file in sorted(schemas):
        with open(schema_file) as f:
            schema = json.load(f)
        
        name = schema_file.stem
        description = schema.get('description', 'No description')
        print(f"\n  {name}")
        print(f"    {description}")
        
        if 'elasticsearch' in schema:
            es_info = schema['elasticsearch']
            print(f"    Index: {es_info.get('index_pattern', 'N/A')}")


def main():
    parser = argparse.ArgumentParser(
        description='Generate test data from schema definition',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # List available schemas
  python generate_test_data.py --list

  # Generate 100 records in JSONL format
  python generate_test_data.py --schema fortify_scans --count 100 --output test.jsonl

  # Generate 50 records in CSV format
  python generate_test_data.py --schema jenkins_builds --count 50 --format csv --output test.csv

  # Generate with custom ID prefix
  python generate_test_data.py --schema fortify_scans --count 10 --base-id FORTIFY
        """
    )
    
    parser.add_argument('--list', '-l', action='store_true',
                       help='List available schemas')
    
    parser.add_argument('--schema', '-s', type=str,
                       help='Schema name (without .json extension)')
    
    parser.add_argument('--count', '-c', type=int, default=10,
                       help='Number of records to generate (default: 10)')
    
    parser.add_argument('--output', '-o', type=str,
                       help='Output file path')
    
    parser.add_argument('--format', '-f', type=str, 
                       choices=['jsonl', 'csv'], default='jsonl',
                       help='Output format (default: jsonl)')
    
    parser.add_argument('--base-id', type=str,
                       help='Base ID prefix for generated records')
    
    args = parser.parse_args()
    
    # List schemas
    if args.list:
        list_schemas()
        return
    
    # Validate arguments
    if not args.schema:
        parser.error("--schema is required (or use --list to see available schemas)")
    
    # Find schema file
    schema_file = Path('schemas') / f"{args.schema}.json"
    if not schema_file.exists():
        print(f"❌ Schema not found: {schema_file}")
        print("\nRun with --list to see available schemas")
        return
    
    # Generate output filename if not provided
    if not args.output:
        args.output = f"test_data_{args.schema}.{args.format}"
    
    # Generate test data
    print(f"\n🚀 Generating test data...")
    print(f"   Schema: {args.schema}")
    print(f"   Count: {args.count}")
    print(f"   Format: {args.format}")
    print(f"   Output: {args.output}")
    
    generator = TestDataGenerator(str(schema_file))
    records = generator.generate_batch(args.count, args.base_id)
    
    # Save based on format
    if args.format == 'jsonl':
        save_as_jsonl(records, args.output)
    else:  # csv
        save_as_csv(records, args.output)
    
    print(f"\n✅ Generated {len(records)} records")
    print(f"✅ Saved to: {args.output}")
    
    # Show sample
    print(f"\n📝 Sample record:")
    sample = records[0]
    print(f"   ID: {sample['id']}")
    print(f"   Content preview: {json.dumps(sample['content'], indent=2)[:200]}...")


if __name__ == '__main__':
    main()
