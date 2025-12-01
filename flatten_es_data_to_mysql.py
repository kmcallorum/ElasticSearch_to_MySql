#!/usr/bin/env python3
"""
Elasticsearch to MySQL Converter

Dynamically converts Elasticsearch JSON exports into normalized MySQL relational tables.

Features:
- Auto-discovers schema from JSON structure
- Creates document tables with proper FK relationships
- Arrays of primitives -> junction tables + master tables
- Arrays of objects -> child tables
- Handles reserved column names (id -> prefixed)
- Idempotent loading (skips already-processed documents)
- CLI-driven with configurable options

Usage:
    python flatten_es_data_to_mysql.py -H localhost -u root -p secret -d mydb -t staging_table
    python flatten_es_data_to_mysql.py -H localhost -u root -p secret -d mydb -t es_export --skip event
    python flatten_es_data_to_mysql.py -H localhost -u root -p secret -d mydb -t es_export --discover-only
"""

import mysql.connector
import json
import argparse
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional

# Reserved column names that need prefixing
RESERVED_COLUMNS = {'id', 'parent_id', '_id', '_index', '_version'}


def get_mysql_type(value):
    """Infer MySQL column type from Python value"""
    if value is None:
        return "TEXT"
    elif isinstance(value, bool):
        return "BOOLEAN"
    elif isinstance(value, int):
        return "BIGINT"
    elif isinstance(value, float):
        return "DOUBLE"
    elif isinstance(value, (dict, list)):
        return "JSON"
    elif len(str(value)) > 255:
        return "TEXT"
    else:
        return "VARCHAR(255)"


def sanitize_name(name: str, table_name: str = None) -> str:
    """Convert JSON key to valid MySQL column name, handling reserved words"""
    sanitized = name.replace('@', '').replace(' ', '_').replace('-', '_')
    sanitized = ''.join(c if c.isalnum() or c == '_' else '_' for c in sanitized)
    sanitized = sanitized.lower().strip('_')
    
    # Handle reserved column names
    if sanitized in RESERVED_COLUMNS:
        if table_name:
            parts = table_name.replace('document_', '').split('_')
            prefix = parts[-1] if parts else 'src'
        else:
            prefix = 'src'
        sanitized = f"{prefix}_{sanitized}"
    
    return sanitized


def sanitize_table_name(name: str) -> str:
    """Convert JSON key to valid MySQL table name"""
    sanitized = name.replace('@', '').replace(' ', '_').replace('-', '_')
    sanitized = ''.join(c if c.isalnum() or c == '_' else '_' for c in sanitized)
    return sanitized.lower().strip('_')


@dataclass 
class SchemaConfig:
    """Configuration for schema generation"""
    skip_paths: List[str] = field(default_factory=list)
    keep_as_json: List[str] = field(default_factory=list)
    master_overrides: Dict[str, str] = field(default_factory=dict)


class ElasticsearchToMySQL:
    """
    Dynamically converts Elasticsearch documents to relational MySQL tables.
    
    - Scans sample records to discover all possible fields
    - Detects structure types (nested objects, arrays of objects, arrays of primitives)
    - Creates tables dynamically with auto-increment PKs
    - Adds columns on the fly as new fields appear
    """
    
    def __init__(self, connection, temp_table: str = 'temp_data', 
                 json_column: str = 'content', config: SchemaConfig = None):
        self.conn = connection
        self.temp_table = temp_table
        self.json_column = json_column
        self.config = config or SchemaConfig()
        
        self.tables = {}           # table_name -> {columns: {name: type}, path: str, parent: str}
        self.column_cache = {}     # table_name -> set of column names (for fast lookup)
        self.master_cache = {}     # master_table -> {value: id}
        self.junction_tables = {}  # For arrays of primitives
        self.master_tables = {}    # Master lookup tables
        self.pending_arrays = {}   # Arrays we've seen empty, path -> parent_table
        
        self._schema_discovered = False
    
    def _get_path(self, parent_path: str, key: str) -> str:
        """Build dot-notation path"""
        return f"{parent_path}.{key}" if parent_path else key
    
    def _get_table_name(self, path: str) -> str:
        """
        Convert JSON path to table name.
        '' -> 'document'
        'Event' -> 'document_event'
        'pipelineData.pipelineLibraries' -> 'document_pipelinedata_pipelinelibraries'
        """
        if not path:
            return 'document'
        
        parts = path.split('.')
        sanitized_parts = [sanitize_table_name(p) for p in parts]
        return 'document_' + '_'.join(sanitized_parts)
    
    def _should_skip(self, path: str) -> bool:
        """Check if path should be skipped"""
        for skip in self.config.skip_paths:
            if path == skip or path.startswith(skip + '.'):
                return True
        return False
    
    def _should_keep_as_json(self, path: str) -> bool:
        """Check if path should be stored as JSON blob"""
        return path in self.config.keep_as_json
    
    def _ensure_column(self, table_name: str, col_name: str, col_type: str):
        """Add column to table schema if not exists"""
        if table_name not in self.tables:
            self.tables[table_name] = {'columns': {}, 'path': '', 'parent': None}
            self.column_cache[table_name] = set()
        
        if col_name not in self.column_cache[table_name]:
            self.tables[table_name]['columns'][col_name] = col_type
            self.column_cache[table_name].add(col_name)
    
    def _ensure_master_table(self, path: str, parent_table: str) -> str:
        """Create or get master table for array of primitives"""
        # Use last part of path for master table name
        parts = path.split('.')
        master_name = sanitize_table_name(parts[-1]) + '_master'
        
        if master_name not in self.master_tables:
            self.master_tables[master_name] = {
                'source_path': path,
                'columns': {'id': 'INT AUTO_INCREMENT PRIMARY KEY', 'value': 'VARCHAR(500) UNIQUE'}
            }
            self.master_cache[master_name] = {}
        
        # Create junction table
        junction_name = f"{parent_table}_{sanitize_table_name(parts[-1])}"
        if junction_name not in self.junction_tables:
            self.junction_tables[junction_name] = {
                'parent_table': parent_table,
                'master_table': master_name,
                'source_path': path
            }
        
        return master_name
    
    def _analyze_value(self, value: Any, path: str, parent_table: str):
        """Recursively analyze a value and update schema"""
        if self._should_skip(path):
            return
        
        if self._should_keep_as_json(path):
            col_name = sanitize_name(path.split('.')[-1], parent_table)
            self._ensure_column(parent_table, col_name, 'JSON')
            return
        
        if isinstance(value, dict):
            # Nested object -> child table
            table_name = self._get_table_name(path)
            if table_name not in self.tables:
                self.tables[table_name] = {
                    'columns': {},
                    'path': path,
                    'parent': parent_table
                }
                self.column_cache[table_name] = set()
            
            for k, v in value.items():
                child_path = self._get_path(path, k)
                if isinstance(v, dict):
                    self._analyze_value(v, child_path, table_name)
                elif isinstance(v, list):
                    self._analyze_value(v, child_path, table_name)
                else:
                    col_name = sanitize_name(k, table_name)
                    col_type = get_mysql_type(v)
                    self._ensure_column(table_name, col_name, col_type)
        
        elif isinstance(value, list):
            if len(value) == 0:
                # Empty array - mark as pending
                self.pending_arrays[path] = parent_table
                return
            
            first = value[0]
            if isinstance(first, dict):
                # Array of objects -> child table
                table_name = self._get_table_name(path)
                if table_name not in self.tables:
                    self.tables[table_name] = {
                        'columns': {},
                        'path': path,
                        'parent': parent_table,
                        'is_array': True
                    }
                    self.column_cache[table_name] = set()
                
                for item in value:
                    if isinstance(item, dict):
                        for k, v in item.items():
                            if isinstance(v, (dict, list)):
                                child_path = self._get_path(path, k)
                                self._analyze_value(v, child_path, table_name)
                            else:
                                col_name = sanitize_name(k, table_name)
                                col_type = get_mysql_type(v)
                                self._ensure_column(table_name, col_name, col_type)
            else:
                # Array of primitives -> junction + master table
                self._ensure_master_table(path, parent_table)
                # Remove from pending if it was there
                if path in self.pending_arrays:
                    del self.pending_arrays[path]
    
    def discover_schema(self, sample_size: int = 100):
        """Scan sample documents to discover schema"""
        print("=" * 60)
        print("SCHEMA DISCOVERY")
        print("=" * 60)
        
        cursor = self.conn.cursor()
        cursor.execute(f"SELECT {self.json_column} FROM {self.temp_table} LIMIT %s", (sample_size,))
        
        # Initialize root table
        self.tables['document'] = {
            'columns': {},
            'path': '',
            'parent': None
        }
        self.column_cache['document'] = set()
        
        doc_count = 0
        for (json_data,) in cursor:
            doc_count += 1
            try:
                doc = json.loads(json_data) if isinstance(json_data, str) else json_data
            except json.JSONDecodeError:
                continue
            
            # Handle ES wrapper (_source)
            source = doc.get('_source', doc)
            
            # Capture ES metadata at root level
            for meta_key in ['_id', '_index', '_version']:
                if meta_key in doc:
                    col_name = sanitize_name(meta_key, 'document')
                    self._ensure_column('document', col_name, get_mysql_type(doc[meta_key]))
            
            # Analyze _source content
            for key, value in source.items():
                path = key
                if isinstance(value, dict):
                    self._analyze_value(value, path, 'document')
                elif isinstance(value, list):
                    self._analyze_value(value, path, 'document')
                else:
                    col_name = sanitize_name(key, 'document')
                    col_type = get_mysql_type(value)
                    self._ensure_column('document', col_name, col_type)
        
        cursor.close()
        
        self._schema_discovered = True
        self._print_schema_summary()
    
    def _print_schema_summary(self):
        """Print discovered schema"""
        print(f"\nSampled documents for schema discovery")
        print(f"Document tables: {len(self.tables)}")
        print(f"Master tables:   {len(self.master_tables)}")
        print(f"Junction tables: {len(self.junction_tables)}")
        
        if self.pending_arrays:
            print(f"Pending arrays (empty in sample): {len(self.pending_arrays)}")
        
        print("=" * 60)
        
        print("\nDOCUMENT TABLES:")
        for name, info in sorted(self.tables.items()):
            cols = list(info['columns'].keys())
            print(f"  {name}")
            print(f"    path: {info['path'] or '/'}")
            print(f"    parent: {info['parent'] or 'ROOT'}")
            print(f"    columns: {len(cols)} ({', '.join(cols[:5])}{'...' if len(cols) > 5 else ''})")
        
        if self.master_tables:
            print("\nMASTER TABLES:")
            for name, info in sorted(self.master_tables.items()):
                print(f"  {name}")
                print(f"    source: {info['source_path']}")
        
        if self.junction_tables:
            print("\nJUNCTION TABLES:")
            for name, info in sorted(self.junction_tables.items()):
                print(f"  {name} -> {info['master_table']}")
        
        print()
    
    def create_tables(self):
        """Create all discovered tables in MySQL"""
        if not self._schema_discovered:
            raise RuntimeError("Must run discover_schema() first")
        
        cursor = self.conn.cursor()
        
        # Create document tables (parent first)
        created_tables = set()
        
        def create_table(name):
            if name in created_tables or name is None:
                return
            
            info = self.tables[name]
            
            # Create parent first
            if info['parent'] and info['parent'] not in created_tables:
                create_table(info['parent'])
            
            cols = ["id INT AUTO_INCREMENT PRIMARY KEY"]
            
            # Add parent_id FK if has parent
            if info['parent']:
                cols.append(f"parent_id INT")
            
            # Add discovered columns
            for col_name, col_type in info['columns'].items():
                cols.append(f"`{col_name}` {col_type}")
            
            sql = f"CREATE TABLE IF NOT EXISTS `{name}` ({', '.join(cols)})"
            print(f"Creating table: {name}")
            cursor.execute(sql)
            created_tables.add(name)
        
        for table_name in self.tables:
            create_table(table_name)
        
        # Create master tables
        for name, info in self.master_tables.items():
            cols = [f"`{k}` {v}" for k, v in info['columns'].items()]
            sql = f"CREATE TABLE IF NOT EXISTS `{name}` ({', '.join(cols)})"
            print(f"Creating master table: {name}")
            cursor.execute(sql)
        
        # Create junction tables
        for name, info in self.junction_tables.items():
            sql = f"""
                CREATE TABLE IF NOT EXISTS `{name}` (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    parent_id INT,
                    master_id INT
                )
            """
            print(f"Creating junction table: {name}")
            cursor.execute(sql)
        
        self.conn.commit()
        cursor.close()
        print(f"\nCreated {len(created_tables)} document tables, "
              f"{len(self.master_tables)} master tables, "
              f"{len(self.junction_tables)} junction tables")
    
    def _add_column_if_missing(self, cursor, table_name: str, col_name: str, col_type: str):
        """Dynamically add column if it doesn't exist"""
        if col_name not in self.column_cache.get(table_name, set()):
            try:
                cursor.execute(f"ALTER TABLE `{table_name}` ADD COLUMN `{col_name}` {col_type}")
                self.conn.commit()
                if table_name not in self.column_cache:
                    self.column_cache[table_name] = set()
                self.column_cache[table_name].add(col_name)
                print(f"  Added column: {table_name}.{col_name}")
            except mysql.connector.Error as e:
                if e.errno != 1060:  # Duplicate column
                    raise
    
    def _get_or_create_master_id(self, cursor, master_table: str, value: str) -> int:
        """Get or create master table entry, return ID"""
        if master_table not in self.master_cache:
            self.master_cache[master_table] = {}
        
        cache = self.master_cache[master_table]
        
        if value in cache:
            return cache[value]
        
        # Try to find existing
        cursor.execute(f"SELECT id FROM `{master_table}` WHERE value = %s", (value,))
        row = cursor.fetchone()
        
        if row:
            cache[value] = row[0]
            return row[0]
        
        # Insert new
        cursor.execute(f"INSERT INTO `{master_table}` (value) VALUES (%s)", (value,))
        new_id = cursor.lastrowid
        cache[value] = new_id
        return new_id
    
    def _insert_row(self, cursor, table_name: str, data: dict, parent_id: int = None) -> int:
        """Insert a row and return its ID"""
        cols = []
        vals = []
        placeholders = []
        
        if parent_id is not None:
            cols.append('parent_id')
            vals.append(parent_id)
            placeholders.append('%s')
        
        for col_name, value in data.items():
            # Dynamically add column if needed
            col_type = get_mysql_type(value)
            self._add_column_if_missing(cursor, table_name, col_name, col_type)
            
            cols.append(f'`{col_name}`')
            
            # Convert complex types to JSON
            if isinstance(value, (dict, list)):
                vals.append(json.dumps(value))
            else:
                vals.append(value)
            placeholders.append('%s')
        
        if not cols:
            # Empty row, just parent_id
            if parent_id is not None:
                cursor.execute(f"INSERT INTO `{table_name}` (parent_id) VALUES (%s)", (parent_id,))
            else:
                cursor.execute(f"INSERT INTO `{table_name}` () VALUES ()")
        else:
            sql = f"INSERT INTO `{table_name}` ({', '.join(cols)}) VALUES ({', '.join(placeholders)})"
            cursor.execute(sql, vals)
        
        return cursor.lastrowid
    
    def _process_document(self, cursor, doc: dict):
        """Process a single ES document"""
        source = doc.get('_source', doc)
        
        # Build root document data
        root_data = {}
        
        # Capture ES metadata
        for meta_key in ['_id', '_index', '_version']:
            if meta_key in doc:
                col_name = sanitize_name(meta_key, 'document')
                root_data[col_name] = doc[meta_key]
        
        # Process all fields
        nested_objects = {}
        arrays = {}
        
        for key, value in source.items():
            path = key
            
            if self._should_skip(path):
                continue
            
            if self._should_keep_as_json(path):
                col_name = sanitize_name(key, 'document')
                root_data[col_name] = value
            elif isinstance(value, dict):
                nested_objects[path] = value
            elif isinstance(value, list):
                arrays[path] = value
            else:
                col_name = sanitize_name(key, 'document')
                root_data[col_name] = value
        
        # Insert root document
        doc_id = self._insert_row(cursor, 'document', root_data)
        
        # Process nested objects
        for path, obj in nested_objects.items():
            self._process_nested_object(cursor, path, obj, doc_id, 'document')
        
        # Process arrays
        for path, arr in arrays.items():
            self._process_array(cursor, path, arr, doc_id, 'document')
    
    def _process_nested_object(self, cursor, path: str, obj: dict, parent_id: int, parent_table: str):
        """Process a nested object (create child row)"""
        if self._should_skip(path):
            return
        
        table_name = self._get_table_name(path)
        
        # Ensure table exists
        if table_name not in self.tables:
            self.tables[table_name] = {'columns': {}, 'path': path, 'parent': parent_table}
            self.column_cache[table_name] = set()
            cursor.execute(f"""
                CREATE TABLE IF NOT EXISTS `{table_name}` (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    parent_id INT
                )
            """)
        
        row_data = {}
        nested = {}
        arrays = {}
        
        for key, value in obj.items():
            child_path = self._get_path(path, key)
            
            if self._should_skip(child_path):
                continue
            
            if self._should_keep_as_json(child_path):
                col_name = sanitize_name(key, table_name)
                row_data[col_name] = value
            elif isinstance(value, dict):
                nested[child_path] = value
            elif isinstance(value, list):
                arrays[child_path] = value
            else:
                col_name = sanitize_name(key, table_name)
                row_data[col_name] = value
        
        row_id = self._insert_row(cursor, table_name, row_data, parent_id)
        
        for child_path, child_obj in nested.items():
            self._process_nested_object(cursor, child_path, child_obj, row_id, table_name)
        
        for child_path, arr in arrays.items():
            self._process_array(cursor, child_path, arr, row_id, table_name)
    
    def _process_array(self, cursor, path: str, arr: list, parent_id: int, parent_table: str):
        """Process an array (objects -> child table, primitives -> junction)"""
        if self._should_skip(path) or len(arr) == 0:
            return
        
        first = arr[0]
        
        if isinstance(first, dict):
            # Array of objects -> child table rows
            table_name = self._get_table_name(path)
            
            if table_name not in self.tables:
                self.tables[table_name] = {'columns': {}, 'path': path, 'parent': parent_table, 'is_array': True}
                self.column_cache[table_name] = set()
                cursor.execute(f"""
                    CREATE TABLE IF NOT EXISTS `{table_name}` (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        parent_id INT
                    )
                """)
            
            for item in arr:
                if isinstance(item, dict):
                    row_data = {}
                    nested = {}
                    child_arrays = {}
                    
                    for key, value in item.items():
                        child_path = self._get_path(path, key)
                        
                        if self._should_skip(child_path):
                            continue
                        
                        if isinstance(value, dict):
                            nested[child_path] = value
                        elif isinstance(value, list):
                            child_arrays[child_path] = value
                        else:
                            col_name = sanitize_name(key, table_name)
                            row_data[col_name] = value
                    
                    row_id = self._insert_row(cursor, table_name, row_data, parent_id)
                    
                    for child_path, child_obj in nested.items():
                        self._process_nested_object(cursor, child_path, child_obj, row_id, table_name)
                    
                    for child_path, child_arr in child_arrays.items():
                        self._process_array(cursor, child_path, child_arr, row_id, table_name)
        else:
            # Array of primitives -> junction table
            parts = path.split('.')
            master_name = sanitize_table_name(parts[-1]) + '_master'
            junction_name = f"{parent_table}_{sanitize_table_name(parts[-1])}"
            
            # Ensure master table exists
            if master_name not in self.master_tables:
                self.master_tables[master_name] = {
                    'source_path': path,
                    'columns': {'id': 'INT AUTO_INCREMENT PRIMARY KEY', 'value': 'VARCHAR(500) UNIQUE'}
                }
                self.master_cache[master_name] = {}
                cursor.execute(f"""
                    CREATE TABLE IF NOT EXISTS `{master_name}` (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        value VARCHAR(500) UNIQUE
                    )
                """)
            
            # Ensure junction table exists
            if junction_name not in self.junction_tables:
                self.junction_tables[junction_name] = {
                    'parent_table': parent_table,
                    'master_table': master_name,
                    'source_path': path
                }
                cursor.execute(f"""
                    CREATE TABLE IF NOT EXISTS `{junction_name}` (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        parent_id INT,
                        master_id INT
                    )
                """)
            
            # Insert junction entries
            for value in arr:
                if value is not None:
                    str_value = str(value)
                    master_id = self._get_or_create_master_id(cursor, master_name, str_value)
                    cursor.execute(
                        f"INSERT INTO `{junction_name}` (parent_id, master_id) VALUES (%s, %s)",
                        (parent_id, master_id)
                    )
    
    def load(self, batch_size: int = 100):
        """Load all documents from temp table"""
        if not self._schema_discovered:
            raise RuntimeError("Must run discover_schema() first")
        
        cursor = self.conn.cursor()
        
        # Check for already processed documents (idempotent)
        cursor.execute(f"SELECT COUNT(*) FROM `document`")
        existing_count = cursor.fetchone()[0]
        
        cursor.execute(f"SELECT COUNT(*) FROM {self.temp_table}")
        total_count = cursor.fetchone()[0]
        
        if existing_count > 0:
            print(f"Found {existing_count} existing documents. Checking for new ones...")
            # For simplicity, skip if already loaded
            # A more sophisticated approach would track _id
            if existing_count >= total_count:
                print("All documents already loaded. Skipping.")
                cursor.close()
                return
        
        print(f"\nLoading {total_count} documents...")
        
        cursor.execute(f"SELECT {self.json_column} FROM {self.temp_table}")
        
        processed = 0
        errors = 0
        
        for (json_data,) in cursor:
            try:
                doc = json.loads(json_data) if isinstance(json_data, str) else json_data
                self._process_document(cursor, doc)
                processed += 1
                
                if processed % batch_size == 0:
                    self.conn.commit()
                    print(f"  Processed {processed}/{total_count} documents...")
                    
            except Exception as e:
                errors += 1
                print(f"  Error processing document: {e}")
                continue
        
        self.conn.commit()
        cursor.close()
        
        print(f"\nComplete: {processed} documents loaded, {errors} errors")


def parse_args():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(
        description='Convert Elasticsearch JSON exports to MySQL relational tables',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Basic usage
  python flatten_es_data_to_mysql.py -H localhost -u root -p mypassword -d mydb -t staging_table

  # Specify temp table and skip paths
  python flatten_es_data_to_mysql.py -H localhost -u root -p mypassword -d mydb -t es_export --skip event

  # Just discover schema (no changes)
  python flatten_es_data_to_mysql.py -H localhost -u root -p mypassword -d mydb -t es_export --discover-only

  # Create tables but don't load data
  python flatten_es_data_to_mysql.py -H localhost -u root -p mypassword -d mydb -t es_export --create-only
        """
    )
    
    # Connection args
    parser.add_argument('-H', '--host', required=True, help='MySQL host')
    parser.add_argument('-P', '--port', type=int, default=3306, help='MySQL port (default: 3306)')
    parser.add_argument('-u', '--user', required=True, help='MySQL user')
    parser.add_argument('-p', '--password', required=True, help='MySQL password')
    parser.add_argument('-d', '--database', required=True, help='MySQL database')
    
    # Table args
    parser.add_argument('-t', '--temp-table', required=True,
                        help='Source staging table name containing JSON data (required)')
    parser.add_argument('-j', '--json-column', default='content',
                        help='Column name containing JSON data (default: content)')
    
    # Processing args
    parser.add_argument('--sample', type=int, default=100,
                        help='Sample size for schema discovery (default: 100)')
    parser.add_argument('--batch', type=int, default=100,
                        help='Batch size for commits (default: 100)')
    
    # Schema config args
    parser.add_argument('--skip', nargs='*', default=[],
                        help='JSON paths to skip (e.g., --skip event metadata.debug)')
    parser.add_argument('--keep-json', nargs='*', default=[],
                        help='JSON paths to store as JSON instead of flattening')
    
    # Actions
    parser.add_argument('--discover-only', action='store_true',
                        help='Only discover schema, do not create tables or load data')
    parser.add_argument('--create-only', action='store_true',
                        help='Discover and create tables, but do not load data')
    
    return parser.parse_args()


def main():
    args = parse_args()
    
    # Connect
    print(f"Connecting to {args.host}:{args.port}/{args.database}...")
    conn = mysql.connector.connect(
        host=args.host,
        port=args.port,
        user=args.user,
        password=args.password,
        database=args.database
    )
    print("Connected.\n")
    
    # Config
    config = SchemaConfig(
        skip_paths=args.skip,
        keep_as_json=args.keep_json
    )
    
    # Initialize loader
    loader = ElasticsearchToMySQL(
        conn, 
        temp_table=args.temp_table,
        json_column=args.json_column,
        config=config
    )
    
    # Execute based on flags
    loader.discover_schema(sample_size=args.sample)
    
    if args.discover_only:
        print("Discovery complete. Exiting (--discover-only)")
        conn.close()
        return
    
    loader.create_tables()
    
    if args.create_only:
        print("Tables created. Exiting (--create-only)")
        conn.close()
        return
    
    loader.load(batch_size=args.batch)
    
    conn.close()
    print("\nDone.")


if __name__ == '__main__':
    main()
