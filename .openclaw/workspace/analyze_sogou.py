#!/usr/bin/env python3
import os
import sys
import mimetypes
import sqlite3
import json
import pickle
import plistlib
import hashlib
from pathlib import Path
import textwrap
import re
from datetime import datetime
import struct

def get_file_type(filepath):
    """Determine file type based on content and extension"""
    if not os.path.exists(filepath):
        return "not_found"
    
    # Get MIME type
    mime_type, encoding = mimetypes.guess_type(filepath)
    
    # Check if it's a directory
    if os.path.isdir(filepath):
        return "directory"
    
    # Check file size
    size = os.path.getsize(filepath)
    if size == 0:
        return "empty_file"
    
    # Get file extension
    ext = os.path.splitext(filepath)[1].lower()
    
    # Common file type detection
    if ext in ['.db', '.sqlite', '.sqlite3']:
        return "sqlite_database"
    elif ext in ['.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp']:
        return "image"
    elif ext in ['.xml', '.plist']:
        return "xml/plist"
    elif ext in ['.json']:
        return "json"
    elif ext in ['.txt', '.log']:
        return "text"
    elif ext in ['.dat']:
        return "binary_data"
    elif ext in ['.webp']:
        return "webp_image"
    elif ext in ['.cache']:
        return "cache"
    
    # Try to read first few bytes for magic numbers
    try:
        with open(filepath, 'rb') as f:
            header = f.read(16)
            
        # Check for SQLite
        if header.startswith(b'SQLite format 3'):
            return "sqlite_database"
        # Check for PNG
        elif header.startswith(b'\x89PNG\r\n\x1a\n'):
            return "png_image"
        # Check for JPEG
        elif header.startswith(b'\xff\xd8\xff'):
            return "jpeg_image"
        # Check for GIF
        elif header.startswith(b'GIF87a') or header.startswith(b'GIF89a'):
            return "gif_image"
        # Check for WebP
        elif header.startswith(b'RIFF') and header[8:12] == b'WEBP':
            return "webp_image"
        # Check for Android property file
        elif b'=' in header and b'\n' in header:
            # Might be a property file
            return "properties"
        # Check for binary plist
        elif header.startswith(b'bplist'):
            return "binary_plist"
    except:
        pass
    
    # Try to read as text
    try:
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            sample = f.read(1000)
            if all(ord(c) < 128 or c in '\n\r\t' for c in sample):
                return "likely_text"
    except:
        pass
    
    return f"unknown ({mime_type})"

def analyze_sqlite_database(db_path):
    """Analyze SQLite database structure"""
    results = {
        "tables": [],
        "row_counts": {},
        "sample_data": {}
    }
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Get all tables
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()
        
        for table in tables:
            table_name = table[0]
            results["tables"].append(table_name)
            
            # Get row count
            try:
                cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
                count = cursor.fetchone()[0]
                results["row_counts"][table_name] = count
                
                # Get sample rows (limit to 3)
                if count > 0:
                    try:
                        cursor.execute(f"SELECT * FROM {table_name} LIMIT 3")
                        sample = cursor.fetchall()
                        # Convert to string representation
                        cols = [desc[0] for desc in cursor.description]
                        sample_str = []
                        for row in sample:
                            row_dict = {}
                            for i, col in enumerate(cols):
                                val = row[i]
                                if isinstance(val, (str, int, float)):
                                    row_dict[col] = str(val)[:100]  # Truncate long values
                                elif val is None:
                                    row_dict[col] = "NULL"
                                else:
                                    row_dict[col] = f"<binary:{len(val) if val else 0} bytes>"
                            sample_str.append(row_dict)
                        results["sample_data"][table_name] = sample_str
                    except:
                        results["sample_data"][table_name] = "Unable to read data"
            except:
                results["row_counts"][table_name] = "error"
        
        conn.close()
    except Exception as e:
        results["error"] = str(e)
    
    return results

def analyze_text_file(filepath, max_lines=20):
    """Analyze text file content"""
    results = {}
    
    try:
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            lines = f.readlines()
            results["line_count"] = len(lines)
            results["sample"] = lines[:max_lines]
            
            # Look for patterns
            content = ''.join(lines[:100])  # First 100 lines
            if re.search(r'[a-zA-Z]{3,}', content):
                results["contains_english"] = True
            if re.search(r'[\u4e00-\u9fff]', content):
                results["contains_chinese"] = True
            if re.search(r'\d{4}-\d{2}-\d{2}', content):
                results["contains_dates"] = True
            if 'http://' in content or 'https://' in content:
                results["contains_urls"] = True
                
    except Exception as e:
        results["error"] = str(e)
    
    return results

def analyze_binary_file(filepath, max_bytes=256):
    """Analyze binary file"""
    results = {}
    
    try:
        with open(filepath, 'rb') as f:
            data = f.read(max_bytes)
            results["size"] = os.path.getsize(filepath)
            results["hex_sample"] = data.hex()[:100]
            results["ascii_sample"] = ''.join(chr(b) if 32 <= b < 127 else '.' for b in data[:50])
            
            # Check for common patterns
            if b'<?xml' in data:
                results["likely_xml"] = True
            if b'{' in data and b'}' in data:
                results["likely_json"] = True
            if b'<plist' in data:
                results["likely_plist"] = True
                
    except Exception as e:
        results["error"] = str(e)
    
    return results

def analyze_image_file(filepath):
    """Get basic image info"""
    results = {}
    
    try:
        size = os.path.getsize(filepath)
        results["size"] = size
        results["format"] = os.path.splitext(filepath)[1].lower()
        
        # For webp, we can try to get dimensions
        if filepath.endswith('.webp'):
            with open(filepath, 'rb') as f:
                data = f.read(30)
                # Simple WebP header check
                if data.startswith(b'RIFF') and data[8:12] == b'WEBP':
                    results["is_valid_webp"] = True
                    
    except Exception as e:
        results["error"] = str(e)
    
    return results

def analyze_properties_file(filepath):
    """Analyze Java-style properties file"""
    results = {"properties": {}}
    
    try:
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    results["properties"][key.strip()] = value.strip()
                    
    except Exception as e:
        results["error"] = str(e)
    
    return results

def analyze_directory_structure(root_dir):
    """Walk through directory and analyze all files"""
    analysis = {}
    
    for root, dirs, files in os.walk(root_dir):
        for file in files:
            filepath = os.path.join(root, file)
            rel_path = os.path.relpath(filepath, root_dir)
            
            print(f"Analyzing: {rel_path}")
            
            file_info = {
                "path": rel_path,
                "full_path": filepath,
                "size": os.path.getsize(filepath),
                "modified": datetime.fromtimestamp(os.path.getmtime(filepath)).isoformat(),
                "type": get_file_type(filepath)
            }
            
            # Detailed analysis based on type
            if file_info["type"] == "sqlite_database":
                file_info["database_analysis"] = analyze_sqlite_database(filepath)
            elif file_info["type"] in ["text", "likely_text", "properties"]:
                if "properties" in file_info["type"]:
                    file_info["properties_analysis"] = analyze_properties_file(filepath)
                else:
                    file_info["text_analysis"] = analyze_text_file(filepath)
            elif file_info["type"] in ["image", "png_image", "jpeg_image", "gif_image", "webp_image"]:
                file_info["image_analysis"] = analyze_image_file(filepath)
            elif file_info["type"] not in ["directory", "empty_file"]:
                file_info["binary_analysis"] = analyze_binary_file(filepath)
            
            analysis[rel_path] = file_info
            
            # Export text data if found
            if "text_analysis" in file_info and file_info["text_analysis"].get("sample"):
                export_dir = os.path.join(root_dir, "..", "exported_text")
                os.makedirs(export_dir, exist_ok=True)
                
                export_path = os.path.join(export_dir, f"{hashlib.md5(rel_path.encode()).hexdigest()[:8]}.txt")
                try:
                    with open(filepath, 'r', encoding='utf-8', errors='ignore') as src:
                        content = src.read()
                    with open(export_path, 'w', encoding='utf-8') as dst:
                        dst.write(f"=== Source: {rel_path} ===\n")
                        dst.write(f"Size: {file_info['size']} bytes\n")
                        dst.write(f"Modified: {file_info['modified']}\n")
                        dst.write("=" * 50 + "\n\n")
                        dst.write(content)
                    file_info["exported_to"] = export_path
                except:
                    pass
            
            # Export database content
            if file_info["type"] == "sqlite_database" and "database_analysis" in file_info:
                export_dir = os.path.join(root_dir, "..", "exported_databases")
                os.makedirs(export_dir, exist_ok=True)
                
                db_hash = hashlib.md5(rel_path.encode()).hexdigest()[:8]
                export_path = os.path.join(export_dir, f"{db_hash}_structure.txt")
                try:
                    with open(export_path, 'w', encoding='utf-8') as f:
                        f.write(f"=== Database: {rel_path} ===\n")
                        f.write(f"Size: {file_info['size']} bytes\n")
                        f.write(f"Modified: {file_info['modified']}\n\n")
                        
                        db_info = file_info["database_analysis"]
                        f.write(f"Tables: {len(db_info.get('tables', []))}\n")
                        for table in db_info.get('tables', []):
                            f.write(f"\nTable: {table}\n")
                            f.write(f"  Rows: {db_info.get('row_counts', {}).get(table, 'unknown')}\n")
                            
                            if table in db_info.get('sample_data', {}):
                                sample = db_info['sample_data'][table]
                                if isinstance(sample, list):
                                    f.write("  Sample data:\n")
                                    for i, row in enumerate(sample[:3]):
                                        f.write(f"    Row {i+1}: {row}\n")
                    file_info["db_exported_to"] = export_path
                except Exception as e:
                    print(f"Error exporting database info: {e}")
    
    return analysis

def generate_summary_report(analysis, output_file):
    """Generate a comprehensive summary report"""
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write("=" * 80 + "\n")
        f.write("SOGOU INPUT METHOD DATA ANALYSIS REPORT\n")
        f.write("=" * 80 + "\n\n")
        
        # Count files by type
        type_counts = {}
        total_size = 0
        
        for rel_path, info in analysis.items():
            file_type = info["type"]
            type_counts[file_type] = type_counts.get(file_type, 0) + 1
            total_size += info["size"]
        
        f.write("SUMMARY STATISTICS:\n")
        f.write(f"Total files analyzed: {len(analysis)}\n")
        f.write(f"Total data size: {total_size / 1024 / 1024:.2f} MB\n\n")
        
        f.write("File types found:\n")
        for file_type, count in sorted(type_counts.items(), key=lambda x: x[1], reverse=True):
            f.write(f"  {file_type}: {count} files\n")
        
        f.write("\n" + "=" * 80 + "\n")
        f.write("DETAILED ANALYSIS:\n")
        f.write("=" * 80 + "\n\n")
        
        # Group by directory
        dir_files = {}
        for rel_path, info in analysis.items():
            dir_name = os.path.dirname(rel_path)
            if dir_name == "":
                dir_name = "(root)"
            if dir_name not in dir_files:
                dir_files[dir_name] = []
            dir_files[dir_name].append((rel_path, info))
        
        for dir_name in sorted(dir_files.keys()):
            f.write(f"\nDIRECTORY: {dir_name}/\n")
            f.write("-" * 60 + "\n")
            
            for rel_path, info in sorted(dir_files[dir_name], key=lambda x: x[0]):
                f.write(f"\n  {rel_path}\n")
                f.write(f"    Type: {info['type']}\n")
                f.write(f"    Size: {info['size']} bytes\n")
                f.write(f"    Modified: {info['modified']}\n")
                
                # Add type-specific info
                if info['type'] == 'sqlite_database' and 'database_analysis' in info:
                    db_info = info['database_analysis']
                    table_count = len(db_info.get('tables', []))
                    f.write(f"    SQLite Database: {table_count} tables\n")
                    
                elif 'text_analysis' in info:
                    text_info = info['text_analysis']
                    f.write(f"    Text file: {text_info.get('line_count', '?')} lines\n")
                    
                elif 'image_analysis' in info:
                    img_info = info['image_analysis']
                    f.write(f"    Image: {img_info.get('format', 'unknown')}")
                    if 'size' in img_info:
                        f.write(f", {img_info['size']} bytes")
                    f.write("\n")
                
                if 'exported_to' in info:
                    f.write(f"    [Exported text to: {info['exported_to']}]\n")
                if 'db_exported_to' in info:
                    f.write(f"    [Database structure exported to: {info['db_exported_to']}]\n")

def main():
    # Target directory
    target_dir = "/workspaces/containerOpenclaw/.openclaw/workspace/com.sohu.inputmethod.sogou.xiaomi"
    
    if not os.path.exists(target_dir):
        print(f"Error: Directory not found: {target_dir}")
        return
    
    print(f"Starting analysis of Sogou input method directory: {target_dir}")
    print(f"Total size: {sum(os.path.getsize(os.path.join(dirpath, f)) for dirpath, dirnames, filenames in os.walk(target_dir) for f in filenames) / 1024 / 1024:.2f} MB")
    
    # Analyze directory
    analysis = analyze_directory_structure(target_dir)
    
    # Generate reports
    report_file = os.path.join(target_dir, "..", "sogou_analysis_report.txt")
    generate_summary_report(analysis, report_file)
    
    print(f"\nAnalysis complete!")
    print(f"Report saved to: {report_file}")
    print(f"Exported text files to: {os.path.join(target_dir, '..', 'exported_text')}")
    print(f"Exported database info to: {os.path.join(target_dir, '..', 'exported_databases')}")
    
    # Print interesting findings
    print("\nINTERESTING FINDINGS:")
    
    # Look for databases with user data
    user_data_files = []
    for rel_path, info in analysis.items():
        if info["type"] == "sqlite_database":
            db_info = info.get("database_analysis", {})
            tables = db_info.get("tables", [])
            for table in tables:
                if any(keyword in table.lower() for keyword in ['user', 'history', 'word', 'dict', 'cache', 'config']):
                    user_data_files.append((rel_path, table, db_info.get("row_counts", {}).get(table, 0)))
    
    if user_data_files:
        print("\nPotential user data databases:")
        for path, table, rows in user_data_files[:10]:  # Show top 10
            print(f"  {path}: table '{table}' has {rows} rows")
    
    # Look for large text/log files
    large_text = []
    for rel_path, info in analysis.items():
        if info["type"] in ["text", "likely_text", "properties"] and info["size"] > 1024:  # > 1KB
            large_text.append((rel_path, info["size"]))
    
    if large_text:
        print("\nLarge text files (>1KB):")
        for path, size in sorted(large_text, key=lambda x: x[1], reverse=True)[:10]:
            print(f"  {path}: {size} bytes")

if __name__ == "__main__":
    main()