#!/usr/bin/env python3
"""
Create properly formatted CSV with JSON content

Author: Mac McAllorum
"""
import json
import csv

# Your real ES document
records = [
    {
        "id": "____0XYBQ1N8iksWtSLK",
        "content": {
            "@version": "1",
            "eventData": {
                "type": "pipeline.quality_scan.fortify",
                "status": "success",
                "duration_ms": 0,
                "timestamp_ms": 1609840946994,
                "reportingTool": "jenkins",
                "reportingToolURL": "https://jenkins-ap-main.origin-elr-core-nonprod.optum.com/"
            },
            "@timestamp": "2021-01-05T10:02:44.964Z",
            "fortifyData": {
                "scanType": "full",
                "fortifyIssues": "Critical-102/High-21/Medium-6/Low:1553",
                "scarProjectName": "SPBFinancialProtectionPortals_UHGWM110-025125",
                "fortifyBuildName": "46089",
                "scarProjectVersion": "tpa-ap-claims-web",
                "translateExclusions": "none"
            },
            "pipelineData": {
                "askId": ["UHGWM110-025125"],
                "gitURL": "https://github.optum.com/adaptive-portal/tpa-ap-claims-web.git",
                "caAgileId": "unknown",
                "eventTool": "fortify",
                "gitBranch": "FP-20081",
                "gitCommit": "a756bc123505c758ef3405e9d6acded924b42946",
                "isTestMode": False,
                "pipelineId": "tpa-ap-claims-web.FP-20081-1.41.0.63482",
                "projectKey": "com.optum.tpa.tpa-ap-claims-web",
                "eventToolVersion": "Fortify_SCA_and_Apps_19.1.2"
            },
            "qualityScanData": {
                "resultsURL": "https://scar.uhc.com/ssc"
            }
        }
    },
    {
        "id": "____1ABC456DEF789GH",
        "content": {
            "@version": "1",
            "eventData": {
                "type": "pipeline.quality_scan.fortify",
                "status": "success",
                "duration_ms": 150,
                "timestamp_ms": 1609841046994,
                "reportingTool": "jenkins",
                "reportingToolURL": "https://jenkins-ap-main.origin-elr-core-nonprod.optum.com/"
            },
            "@timestamp": "2021-01-05T10:04:24.964Z",
            "fortifyData": {
                "scanType": "incremental",
                "fortifyIssues": "Critical-50/High-10/Medium-3/Low:800",
                "scarProjectName": "TestProject_UHGWM110-025126",
                "fortifyBuildName": "46090",
                "scarProjectVersion": "test-version",
                "translateExclusions": "none"
            },
            "pipelineData": {
                "askId": ["UHGWM110-025126"],
                "gitURL": "https://github.optum.com/test/test-repo.git",
                "caAgileId": "unknown",
                "eventTool": "fortify",
                "gitBranch": "main",
                "gitCommit": "b856bc123505c758ef3405e9d6acded924b42947",
                "isTestMode": False,
                "pipelineId": "test-project.main-1.42.0.63483",
                "projectKey": "com.optum.test.test-project",
                "eventToolVersion": "Fortify_SCA_and_Apps_19.1.2"
            },
            "qualityScanData": {
                "resultsURL": "https://scar.uhc.com/ssc"
            }
        }
    },
    {
        "id": "____2XYZ789HIJ012KL",
        "content": {
            "@version": "1",
            "eventData": {
                "type": "pipeline.quality_scan.fortify",
                "status": "failure",
                "duration_ms": 200,
                "timestamp_ms": 1609841146994,
                "reportingTool": "jenkins",
                "reportingToolURL": "https://jenkins-ap-main.origin-elr-core-nonprod.optum.com/"
            },
            "@timestamp": "2021-01-05T10:05:24.964Z",
            "fortifyData": {
                "scanType": "full",
                "fortifyIssues": "Critical-200/High-50/Medium-20/Low:2000",
                "scarProjectName": "FailedProject_UHGWM110-025127",
                "fortifyBuildName": "46091",
                "scarProjectVersion": "failed-version",
                "translateExclusions": "none"
            },
            "pipelineData": {
                "askId": ["UHGWM110-025127"],
                "gitURL": "https://github.optum.com/failed/failed-repo.git",
                "caAgileId": "unknown",
                "eventTool": "fortify",
                "gitBranch": "feature",
                "gitCommit": "c956bc123505c758ef3405e9d6acded924b42948",
                "isTestMode": True,
                "pipelineId": "failed-project.feature-1.43.0.63484",
                "projectKey": "com.optum.failed.failed-project",
                "eventToolVersion": "Fortify_SCA_and_Apps_19.1.2"
            },
            "qualityScanData": {
                "resultsURL": "https://scar.uhc.com/ssc"
            }
        }
    }
]

# Write proper CSV (Python's csv module handles escaping correctly)
with open('elasticsearch_proper.csv', 'w', newline='') as f:
    writer = csv.writer(f, quoting=csv.QUOTE_MINIMAL)
    writer.writerow(['id', 'content'])
    
    for record in records:
        # Convert content dict to JSON string
        content_json = json.dumps(record['content'])
        writer.writerow([record['id'], content_json])

print("✅ Created elasticsearch_proper.csv")
print(f"✅ {len(records)} records")
print("\nFirst record preview:")
print(f"ID: {records[0]['id']}")
print(f"Content: {json.dumps(records[0]['content'], indent=2)[:200]}...")
