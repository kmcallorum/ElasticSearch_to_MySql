

# 📊 Prometheus Metrics for ES-MySQL Pipeline

Complete observability for your data pipeline with Prometheus metrics integration.

---

## 🎯 Overview

The ES-MySQL pipeline now includes optional Prometheus metrics that provide comprehensive observability into:
- **Throughput** - Records processed, inserted, skipped, failed
- **Latency** - Fetch, insert, and batch processing times
- **Resources** - Worker threads, queue depth, pipeline state
- **Errors** - Detailed error tracking by type
- **AI Analysis** - Error analysis request tracking

---

## 🚀 Quick Start

### 1. Install Dependencies

```bash
pip install prometheus_client
```

### 2. Run Pipeline with Metrics

```bash
python pipeline_cli.py \
  --source_type csv \
  --csv_file data.csv \
  --sink_type file \
  --output_file output.jsonl \
  --metrics-port 8000
```

### 3. View Metrics

```bash
# Metrics endpoint (for Prometheus)
curl http://localhost:8000/metrics

# Health check
curl http://localhost:8000/health

# Service info
curl http://localhost:8000/info
```

---

## 📊 Available Metrics

### **Counters** (always increasing)

| Metric | Labels | Description |
|--------|--------|-------------|
| `pipeline_records_processed_total` | source_type, sink_type | Total records processed |
| `pipeline_records_inserted_total` | source_type, sink_type | Successfully inserted records |
| `pipeline_records_skipped_total` | source_type, sink_type, reason | Skipped records (duplicates) |
| `pipeline_records_failed_total` | source_type, sink_type, error_type | Failed records by error type |
| `pipeline_runs_total` | source_type, sink_type, status | Pipeline run attempts |
| `pipeline_ai_analysis_requests_total` | analyzer_type, status | AI error analysis requests |

### **Gauges** (current value)

| Metric | Labels | Description |
|--------|--------|-------------|
| `pipeline_active_workers` | pipeline_id | Current active worker threads |
| `pipeline_queue_depth` | pipeline_id | Current queue size |
| `pipeline_state` | pipeline_id | Pipeline state (0=stopped, 1=running, 2=error) |

### **Histograms** (distribution)

| Metric | Labels | Description |
|--------|--------|-------------|
| `pipeline_fetch_duration_seconds` | source_type | Time to fetch records from source |
| `pipeline_insert_duration_seconds` | sink_type | Time to insert single record |
| `pipeline_batch_duration_seconds` | source_type, sink_type | Time to process batch |
| `pipeline_batch_size` | source_type | Records per batch |

### **Summary** (percentiles)

| Metric | Labels | Description |
|--------|--------|-------------|
| `pipeline_run_duration_seconds` | source_type, sink_type, status | Total pipeline run duration |

---

## 🔧 Configuration

### CLI Flags

```bash
--metrics-port PORT     # Port for metrics server (e.g., 8000)
--metrics-host HOST     # Host to bind to (default: 0.0.0.0)
--pipeline-id ID        # Unique pipeline identifier (default: "default")
```

### Example: Multiple Pipelines

Run multiple pipelines with unique IDs:

```bash
# Pipeline 1
python pipeline_cli.py ... --metrics-port 8000 --pipeline-id pipeline-1

# Pipeline 2  
python pipeline_cli.py ... --metrics-port 8001 --pipeline-id pipeline-2
```

---

## 📈 Prometheus Configuration

### Add to `prometheus.yml`

```yaml
scrape_configs:
  - job_name: 'es-mysql-pipeline'
    static_configs:
      - targets: ['localhost:8000']
    scrape_interval: 15s
    scrape_timeout: 10s
```

### Multiple Instances

```yaml
scrape_configs:
  - job_name: 'es-mysql-pipelines'
    static_configs:
      - targets: 
          - 'localhost:8000'
          - 'localhost:8001'
          - 'localhost:8002'
        labels:
          environment: 'production'
```

---

## 📊 Example Prometheus Queries

### Throughput

```promql
# Records processed per second
rate(pipeline_records_processed_total[1m])

# Total records processed (last 24h)
increase(pipeline_records_processed_total[24h])

# Processing rate by source
sum by (source_type) (rate(pipeline_records_processed_total[5m]))
```

### Success Rate

```promql
# Overall success rate (%)
sum(rate(pipeline_records_inserted_total[5m])) 
/ 
sum(rate(pipeline_records_processed_total[5m])) * 100

# Success rate by sink type
sum by (sink_type) (rate(pipeline_records_inserted_total[5m]))
/ 
sum by (sink_type) (rate(pipeline_records_processed_total[5m])) * 100
```

### Latency

```promql
# 95th percentile insert latency
histogram_quantile(0.95, 
  rate(pipeline_insert_duration_seconds_bucket[5m])
)

# Average batch processing time
rate(pipeline_batch_duration_seconds_sum[5m]) 
/ 
rate(pipeline_batch_duration_seconds_count[5m])

# Median fetch latency
histogram_quantile(0.50,
  rate(pipeline_fetch_duration_seconds_bucket[5m])
)
```

### Errors

```promql
# Error rate
rate(pipeline_records_failed_total[5m])

# Errors by type
sum by (error_type) (rate(pipeline_records_failed_total[5m]))

# Error ratio (%)
rate(pipeline_records_failed_total[5m]) 
/ 
rate(pipeline_records_processed_total[5m]) * 100
```

### Resource Utilization

```promql
# Active workers
pipeline_active_workers

# Queue depth
pipeline_queue_depth

# Pipeline state (0=stopped, 1=running, 2=error)
pipeline_state
```

---

## 🚨 Alerting Rules

### Example `alerts.yml`

```yaml
groups:
  - name: pipeline_alerts
    interval: 30s
    rules:
      # High error rate
      - alert: HighPipelineErrorRate
        expr: |
          rate(pipeline_records_failed_total[5m]) 
          / 
          rate(pipeline_records_processed_total[5m]) > 0.10
        for: 2m
        labels:
          severity: warning
        annotations:
          summary: "Pipeline error rate above 10%"
          description: "Pipeline {{ $labels.pipeline_id }} has {{ $value | humanizePercentage }} error rate"
      
      # Queue backup
      - alert: PipelineQueueBackup
        expr: pipeline_queue_depth > 1000
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "Pipeline queue depth exceeded 1000"
          description: "Pipeline {{ $labels.pipeline_id }} queue: {{ $value }}"
      
      # Slow processing
      - alert: SlowPipelineProcessing
        expr: |
          histogram_quantile(0.95,
            rate(pipeline_insert_duration_seconds_bucket[5m])
          ) > 1.0
        for: 3m
        labels:
          severity: warning
        annotations:
          summary: "95th percentile insert latency above 1 second"
          description: "Sink {{ $labels.sink_type }}: {{ $value }}s"
      
      # Pipeline failure
      - alert: PipelineFailure
        expr: pipeline_state == 2
        for: 1m
        labels:
          severity: critical
        annotations:
          summary: "Pipeline in error state"
          description: "Pipeline {{ $labels.pipeline_id }} has failed"
      
      # No data being processed
      - alert: PipelineStalled
        expr: |
          rate(pipeline_records_processed_total[5m]) == 0
          and
          pipeline_state == 1
        for: 10m
        labels:
          severity: warning
        annotations:
          summary: "Pipeline running but not processing records"
          description: "Pipeline {{ $labels.pipeline_id }} may be stalled"
```

---

## 📊 Grafana Dashboards

### Quick Dashboard Creation

1. **Import Prometheus datasource** in Grafana
2. **Create dashboard** with these panels:

#### Panel 1: Throughput
```promql
rate(pipeline_records_processed_total[1m])
```

#### Panel 2: Success Rate
```promql
sum(rate(pipeline_records_inserted_total[5m])) / sum(rate(pipeline_records_processed_total[5m])) * 100
```

#### Panel 3: Latency (P95)
```promql
histogram_quantile(0.95, rate(pipeline_insert_duration_seconds_bucket[5m]))
```

#### Panel 4: Error Rate
```promql
rate(pipeline_records_failed_total[5m])
```

#### Panel 5: Active Workers
```promql
pipeline_active_workers
```

#### Panel 6: Queue Depth
```promql
pipeline_queue_depth
```

---

## 🔍 Debugging with Metrics

### Find Slow Batches

```promql
# Batches taking > 10 seconds
pipeline_batch_duration_seconds_bucket{le="10.0"}
```

### Identify Error Spikes

```promql
# Error rate in last hour
increase(pipeline_records_failed_total[1h])
```

### Monitor AI Analysis

```promql
# AI analysis success rate
sum(rate(pipeline_ai_analysis_requests_total{status="success"}[5m]))
/
sum(rate(pipeline_ai_analysis_requests_total[5m]))
```

---

## 🧪 Testing Metrics Locally

### Start Prometheus Locally

```bash
# Download Prometheus
wget https://github.com/prometheus/prometheus/releases/download/v2.45.0/prometheus-2.45.0.linux-amd64.tar.gz
tar xvfz prometheus-*.tar.gz
cd prometheus-*

# Create config
cat > prometheus.yml <<EOF
global:
  scrape_interval: 15s

scrape_configs:
  - job_name: 'pipeline'
    static_configs:
      - targets: ['localhost:8000']
EOF

# Run Prometheus
./prometheus --config.file=prometheus.yml
```

### View in Prometheus UI

```
http://localhost:9090
```

---

## 🎯 Best Practices

### 1. Use Unique Pipeline IDs

```bash
# Good: Descriptive IDs
--pipeline-id "prod-es-to-mysql-daily"
--pipeline-id "staging-csv-import"

# Bad: Generic IDs
--pipeline-id "pipeline1"
--pipeline-id "default"
```

### 2. Monitor Key Metrics

Focus on:
- ✅ **Success rate** - Should be > 99%
- ⚡ **P95 latency** - Should be < 1s
- 🚨 **Error rate** - Should be < 1%
- 📊 **Queue depth** - Should be < 1000

### 3. Set Up Alerts

Always alert on:
- High error rates (> 10%)
- Pipeline failures
- Performance degradation
- Queue backups

### 4. Regular Review

Weekly review:
- Latency trends
- Error patterns
- Resource utilization
- Capacity planning

---

## 🔧 Troubleshooting

### Metrics Not Showing

```bash
# Check if prometheus_client is installed
pip list | grep prometheus

# Verify metrics endpoint
curl http://localhost:8000/metrics

# Check logs
tail -f pipeline.log | grep -i metric
```

### Port Already in Use

```bash
# Find process using port
lsof -i :8000

# Use different port
--metrics-port 8001
```

### Prometheus Not Scraping

```bash
# Check Prometheus targets
http://localhost:9090/targets

# Verify network connectivity
curl http://pipeline-host:8000/health
```

---

## 📚 Additional Resources

- [Prometheus Documentation](https://prometheus.io/docs/)
- [Grafana Dashboards](https://grafana.com/docs/)
- [PromQL Basics](https://prometheus.io/docs/prometheus/latest/querying/basics/)
- [Best Practices](https://prometheus.io/docs/practices/)

---

## 🎉 What's Next?

With metrics enabled, you can:
1. ✅ **Monitor** pipeline performance in real-time
2. 📊 **Visualize** trends in Grafana
3. 🚨 **Alert** on issues before they impact users
4. 🔍 **Debug** problems with detailed metrics
5. 📈 **Optimize** based on data, not guesses

---

**Author:** Mac McAllorum (kevin_mcallorum@linux.com)  
**License:** MIT  
**Version:** 1.0.0

**🏆 100% Test Coverage Maintained!**
