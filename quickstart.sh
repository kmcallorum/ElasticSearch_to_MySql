#!/bin/bash

# Quick start script to demonstrate the pipeline with test data

echo "================================"
echo "Data Pipeline Quick Start"
echo "================================"
echo ""

# Step 1: Install dependencies
echo "Step 1: Installing dependencies..."
pip install -q -r requirements.txt
echo "✓ Dependencies installed"
echo ""

# Step 2: Generate test data
echo "Step 2: Generating test data..."
python generate_test_data.py
echo "✓ Test data generated"
echo ""

# Step 3: Run the pipeline with test data
echo "Step 3: Running pipeline (CSV → JSONL)..."
python pipeline_cli.py \
  --source_type csv \
  --sink_type jsonl \
  --csv_file test_data_medium.csv \
  --output_file output_test.jsonl \
  --threads 1 \
  --limit 20

echo ""
echo "✓ Pipeline completed"
echo ""

# Step 4: Show results
echo "Step 4: Showing first 5 records from output..."
head -5 output_test.jsonl | python -m json.tool
echo ""

# Step 5: Run tests
echo "Step 5: Running test suite..."
pytest test_pipeline.py -v --tb=short

echo ""
echo "================================"
echo "Quick start completed!"
echo "================================"
echo ""
echo "Next steps:"
echo "  1. Review the output file: output_test.jsonl"
echo "  2. Check the log file: pipeline.log"
echo "  3. Run tests with coverage: pytest test_pipeline.py --cov=. --cov-report=html"
echo "  4. For production use, configure ES and MySQL settings"
echo ""
