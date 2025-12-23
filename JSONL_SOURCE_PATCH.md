# PATCH FOR pipeline_cli.py - Add JSONL Source Support

## Changes needed:

### 1. Add import at top of file:
```python
from jsonl_source import JSONLSource
```

### 2. Update --source_type argument:
```python
parser.add_argument('--source_type', required=True, 
                   choices=['elasticsearch', 'csv', 'jsonl'],  # ← Add 'jsonl'
                   help='Source type')
```

### 3. Add JSONL-specific arguments (after --csv_content_column):
```python
# JSONL source options
parser.add_argument('--jsonl_file', help='Path to JSONL file')
parser.add_argument('--jsonl_id_field', default='id',
                   help='Field name for record ID (default: id)')
parser.add_argument('--jsonl_content_field', default='content',
                   help='Field name for content (default: content, use None for entire record)')
```

### 4. Update create_source() function to add JSONL case:
```python
def create_source(args):
    """Factory function to create appropriate data source"""
    if args.source_type == 'elasticsearch':
        if not args.es_url:
            raise ValueError("--es_url is required for elasticsearch source")
        
        return ElasticsearchSource(
            es_url=args.es_url,
            es_user=args.es_user,
            es_pass=args.es_pass,
            api_key=args.api_key,
            batch_size=args.batch_size
        )
    
    elif args.source_type == 'csv':
        if not args.csv_file:
            raise ValueError("--csv_file is required for CSV source")
        
        return CSVSource(
            filepath=args.csv_file,
            id_column=args.csv_id_column,
            content_column=args.csv_content_column
        )
    
    elif args.source_type == 'jsonl':  # ← ADD THIS
        if not args.jsonl_file:
            raise ValueError("--jsonl_file is required for JSONL source")
        
        content_field = args.jsonl_content_field
        if content_field and content_field.lower() == 'none':
            content_field = None
        
        return JSONLSource(
            filepath=args.jsonl_file,
            id_field=args.jsonl_id_field,
            content_field=content_field
        )
    
    else:
        raise ValueError(f"Unknown source type: {args.source_type}")
```

## Quick way to apply:

Just add these lines to your pipeline_cli.py in the appropriate places!

Or run:
```bash
# Copy the jsonl_source.py file
cp jsonl_source.py .

# Then manually edit pipeline_cli.py to add the above changes
```
