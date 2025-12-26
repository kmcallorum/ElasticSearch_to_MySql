#!/usr/bin/env python3
"""
Script to update MySQL test files to use environment-based configuration.
Adds the import and provides a helper to replace hardcoded MySQL parameters.
"""
import re
import sys
from pathlib import Path


def update_test_file(filepath):
    """Update a test file to use test_config."""
    
    with open(filepath, 'r') as f:
        content = f.read()
    
    original_content = content
    
    # Check if test_config is already imported
    if 'from test_config import' not in content and 'import test_config' not in content:
        # Add import after other imports
        import_pattern = r'^((?:from|import)\s+.+\n)+'
        match = re.search(import_pattern, content, re.MULTILINE)
        if match:
            # Insert after existing imports
            insert_pos = match.end()
            content = (
                content[:insert_pos] + 
                '\nfrom test_config import get_mysql_config\n' +
                content[insert_pos:]
            )
        else:
            # No imports found, add at the top after docstring
            content = 'from test_config import get_mysql_config\n\n' + content
    
    # Pattern to match MySQLSink initialization with hardcoded values
    # This is a complex pattern that matches multiline MySQLSink() calls
    pattern = r'MySQLSink\s*\(\s*(?:host\s*=\s*["\']localhost["\']\s*,?\s*)?(?:port\s*=\s*3306\s*,?\s*)?(?:user\s*=\s*["\']root["\']\s*,?\s*)?(?:password\s*=\s*["\'][^"\']*["\']\s*,?\s*)?(?:database\s*=\s*["\']testdb["\']\s*,?\s*)?(table\s*=\s*["\']records["\']\s*)?\)'
    
    # Add a comment suggesting manual review
    if re.search(pattern, content):
        print(f"  Found MySQLSink instantiation(s) in {filepath}")
        print(f"  Please manually update to use: config = get_mysql_config()")
    
    # Save if changed
    if content != original_content:
        with open(filepath, 'w') as f:
            f.write(content)
        print(f"✅ Updated {filepath} - added import")
        return True
    else:
        print(f"⏭️  {filepath} - no changes needed")
        return False


def main():
    """Update all MySQL test files."""
    
    test_files = [
        'test_production_impl.py',
        'test_production_impl_edge_cases.py',
    ]
    
    print("MySQL Test Configuration Updater")
    print("=" * 50)
    print()
    
    changes_made = False
    
    for filename in test_files:
        filepath = Path(filename)
        if filepath.exists():
            print(f"Processing: {filename}")
            if update_test_file(filepath):
                changes_made = True
            print()
        else:
            print(f"⚠️  File not found: {filename}")
            print()
    
    print("=" * 50)
    if changes_made:
        print("✅ Import statements added!")
        print()
        print("Next steps:")
        print("1. Review the updated files")
        print("2. Manually replace MySQLSink() instantiations with:")
        print("   config = get_mysql_config()")
        print("   MySQLSink(**config, table='records')")
        print()
    else:
        print("No changes were necessary.")
    
    print("See MYSQL_TEST_MIGRATION.md for detailed examples.")


if __name__ == '__main__':
    main()
