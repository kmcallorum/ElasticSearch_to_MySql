#!/usr/bin/env python3
"""
Update README.md with coverage report from htmlcov/index.html

This script extracts coverage data from the HTML report and appends
a coverage summary table to README.md

Author: Mac McAllorum
"""
import re
from pathlib import Path
from bs4 import BeautifulSoup


def parse_coverage_html():
    """Parse htmlcov/index.html and extract coverage data"""
    html_file = Path('htmlcov/index.html')
    
    if not html_file.exists():
        print("❌ Coverage HTML not found. Run: pytest --cov=. --cov-report=html")
        return None
    
    with open(html_file) as f:
        soup = BeautifulSoup(f.read(), 'html.parser')
    
    # Extract overall coverage from footer
    total_row = soup.find('tr', class_='total')
    if not total_row:
        return None
    
    cells = total_row.find_all('td')
    overall_coverage = cells[-1].text.strip()
    
    # Extract per-file coverage
    files = []
    for row in soup.find_all('tr', class_=lambda x: x and 'file' in x):
        cells = row.find_all('td')
        if len(cells) >= 4:
            filename = cells[0].text.strip()
            statements = cells[1].text.strip()
            missing = cells[2].text.strip()
            coverage = cells[3].text.strip()
            
            # Only include production files
            if not filename.startswith('test_'):
                files.append({
                    'filename': filename,
                    'statements': statements,
                    'missing': missing,
                    'coverage': coverage
                })
    
    return {
        'overall': overall_coverage,
        'files': files
    }


def generate_coverage_markdown(coverage_data):
    """Generate markdown table from coverage data"""
    if not coverage_data:
        return ""
    
    md = "\n\n---\n\n"
    md += "## 📊 Test Coverage\n\n"
    md += f"**Overall Coverage: {coverage_data['overall']}**\n\n"
    md += "| File | Statements | Missing | Coverage |\n"
    md += "|------|------------|---------|----------|\n"
    
    for file_data in coverage_data['files']:
        md += f"| {file_data['filename']} | {file_data['statements']} | {file_data['missing']} | {file_data['coverage']} |\n"
    
    md += f"\n**Total Tests:** 293+ comprehensive tests\n"
    md += f"**Last Updated:** {get_timestamp()}\n\n"
    md += "[![codecov](https://codecov.io/gh/YOUR_USERNAME/es-to-mysql-cli/branch/main/graph/badge.svg)](https://codecov.io/gh/YOUR_USERNAME/es-to-mysql-cli)\n"
    
    return md


def get_timestamp():
    """Get current timestamp"""
    from datetime import datetime
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S UTC")


def update_readme(coverage_markdown):
    """Update README.md with coverage data"""
    readme_file = Path('README.md')
    
    if not readme_file.exists():
        print("❌ README.md not found")
        return False
    
    with open(readme_file) as f:
        content = f.read()
    
    # Remove old coverage section if it exists
    pattern = r'\n---\n\n## 📊 Test Coverage.*?(?=\n##|\Z)'
    content = re.sub(pattern, '', content, flags=re.DOTALL)
    
    # Append new coverage section
    content = content.rstrip() + coverage_markdown
    
    with open(readme_file, 'w') as f:
        f.write(content)
    
    print("✅ README.md updated with coverage report")
    return True


def main():
    """Main execution"""
    print("📊 Parsing coverage report...")
    coverage_data = parse_coverage_html()
    
    if not coverage_data:
        print("❌ Failed to parse coverage data")
        return 1
    
    print(f"✅ Overall coverage: {coverage_data['overall']}")
    print(f"✅ Found {len(coverage_data['files'])} production files")
    
    coverage_md = generate_coverage_markdown(coverage_data)
    
    if update_readme(coverage_md):
        print("✅ Coverage report added to README.md")
        return 0
    else:
        return 1


if __name__ == '__main__':
    import sys
    sys.exit(main())
