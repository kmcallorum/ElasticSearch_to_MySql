# 🔧 ADD JSONL SOURCE SUPPORT - COMPLETE GUIDE

## 📦 FILES TO ADD:

### **1. Copy jsonl_source.py to your project:**

```bash
cp jsonl_source.py .
```

### **2. Update pipeline_cli.py - Add these lines:**

#### **A. Add import (around line 14):**

```python
from test_impl import CSVSource, FileSink, JSONLSink
from jsonl_source import JSONLSource  # ← ADD THIS LINE
```

#### **B. Update source_type choices (around line 80):**

```python
parser.add_argument('--source_type', required=True, 
                   choices=['elasticsearch', 'csv', 'jsonl'],  # ← Add 'jsonl'
                   help='Source type')
```

#### **C. Add JSONL arguments (around line 120, after CSV options):**

```python
# JSONL source options
parser.add_argument('--jsonl_file', help='Path to JSONL file')
parser.add_argument('--jsonl_id_field', default='id',
                   help='Field name for record ID (default: id)')
parser.add_argument('--jsonl_content_field', default='content',
                   help='Field name for content (default: content)')
```

#### **D. Update create_source() function (around line 50):**

Add this elif block after the CSV case:

```python
elif args.source_type == "jsonl":
    content_field = args.jsonl_content_field
    if content_field and content_field.lower() == 'none':
        content_field = None
    
    return JSONLSource(
        filepath=args.jsonl_file,
        id_field=args.jsonl_id_field,
        content_field=content_field
    )
```

---

## ✅ OR USE THE QUICK SCRIPT:

```bash
# Create a quick patch script
cat > add_jsonl_support.sh << 'EOF'
#!/bin/bash

# Check if jsonl_source.py exists
if [ ! -f "jsonl_source.py" ]; then
    echo "❌ Error: jsonl_source.py not found"
    echo "   Copy it to current directory first"
    exit 1
fi

# Check if pipeline_cli.py exists
if [ ! -f "pipeline_cli.py" ]; then
    echo "❌ Error: pipeline_cli.py not found"
    exit 1
fi

echo "✅ Files found"
echo ""
echo "📝 Manual steps needed:"
echo ""
echo "1. Open pipeline_cli.py in your editor"
echo ""
echo "2. Add this import (around line 14):"
echo "   from jsonl_source import JSONLSource"
echo ""
echo "3. Change source_type choices (around line 80) to:"
echo "   choices=['elasticsearch', 'csv', 'jsonl']"
echo ""
echo "4. Add JSONL arguments (around line 120):"
echo "   parser.add_argument('--jsonl_file', ...)"
echo "   parser.add_argument('--jsonl_id_field', ...)"
echo "   parser.add_argument('--jsonl_content_field', ...)"
echo ""
echo "5. Add JSONL case in create_source() (around line 50):"
echo "   elif args.source_type == 'jsonl': ..."
echo ""
echo "See JSONL_SOURCE_PATCH.md for exact code to add!"
EOF

chmod +x add_jsonl_support.sh
./add_jsonl_support.sh
```

---

## 🚀 AFTER ADDING SUPPORT:

### **Test it:**

```bash
# 1. Generate test data
mkdir schemas
cp fortify_scans.json schemas/

python generate_test_data_schema.py \
  --schema fortify_scans \
  --count 10 \
  --output test.jsonl

# 2. Run pipeline with JSONL source!
python pipeline_cli.py \
  --source_type jsonl \
  --jsonl_file test.jsonl \
  --sink_type jsonl \
  --output_file output.jsonl \
  --metrics-port 8000

# 3. Check results
cat output.jsonl | jq .
```

---

## 📊 USAGE EXAMPLES:

### **Basic JSONL format (id + content):**

```jsonl
{"id": "rec1", "content": {"name": "Alice"}}
{"id": "rec2", "content": {"name": "Bob"}}
```

```bash
python pipeline_cli.py \
  --source_type jsonl \
  --jsonl_file data.jsonl \
  --sink_type mysql \
  ...
```

### **Custom field names:**

```jsonl
{"doc_id": "123", "data": {"info": "..."}}
{"doc_id": "456", "data": {"info": "..."}}
```

```bash
python pipeline_cli.py \
  --source_type jsonl \
  --jsonl_file data.jsonl \
  --jsonl_id_field doc_id \
  --jsonl_content_field data \
  --sink_type mysql \
  ...
```

### **No ID field (auto-generate from line number):**

```jsonl
{"name": "Alice", "age": 30}
{"name": "Bob", "age": 25}
```

```bash
python pipeline_cli.py \
  --source_type jsonl \
  --jsonl_file data.jsonl \
  --jsonl_id_field _line \
  --jsonl_content_field none \
  --sink_type mysql \
  ...
```

---

## 💪 WHY JSONL IS BETTER THAN CSV FOR THIS:

✅ **No escaping nightmares** - JSON handles nested data  
✅ **Perfect for Elasticsearch** - Same format ES uses  
✅ **Human readable** - Easy to debug  
✅ **Standard format** - Works everywhere  
✅ **Schema agnostic** - ANY JSON structure works  

---

## 🎯 YOUR WORKFLOW BECOMES:

```bash
# 1. Define schema
vi schemas/my_project.json

# 2. Generate test data
python generate_test_data_schema.py --schema my_project --count 100

# 3. Test pipeline
python pipeline_cli.py \
  --source_type jsonl \
  --jsonl_file test_data_my_project.jsonl \
  --sink_type jsonl \
  --output_file output.jsonl

# 4. Production (when ready)
python pipeline_cli.py \
  --source_type elasticsearch \
  --es_host real-es-cluster \
  --sink_type mysql \
  ...
```

---

**Add those 4 small changes to pipeline_cli.py and you're good to go!** 🚀
