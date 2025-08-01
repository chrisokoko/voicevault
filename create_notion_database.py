#!/usr/bin/env python3
"""
Create a fresh Notion database with a specified schema
Usage: python3 create_notion_database.py --schema schema.json --page-id <notion-page-id>
"""

import sys
import os
import json
import argparse
from pathlib import Path

sys.path.append('src')

from notion_client import Client
from config.config import NOTION_TOKEN

def createNotionDatabase(schema_file: str, page_id: str) -> str:
    """
    Create a new Notion database with the specified schema on the given page
    
    Args:
        schema_file: Path to JSON file containing the database schema
        page_id: Notion page ID where the database should be created
        
    Returns:
        Database ID of the created database, or None if failed
    """
    
    # Validate inputs
    if not os.path.exists(schema_file):
        print(f"❌ Schema file not found: {schema_file}")
        return None
    
    if not page_id:
        print("❌ Page ID is required")
        return None
    
    if not NOTION_TOKEN:
        print("❌ NOTION_TOKEN not configured")
        return None
    
    try:
        # Load schema from JSON file
        print(f"📖 Loading schema from: {schema_file}")
        with open(schema_file, 'r') as f:
            schema_data = json.load(f)
        
        database_title = schema_data.get('title', 'Voice Memos')
        database_properties = schema_data.get('properties', {})
        
        print(f"📋 Database title: {database_title}")
        print(f"🏗️  Properties: {len(database_properties)} fields")
        
        # Create the database
        print(f"🔧 Creating database on page: {page_id}")
        
        client = Client(auth=NOTION_TOKEN)
        
        response = client.databases.create(
            parent={
                "type": "page_id",
                "page_id": page_id
            },
            title=[
                {
                    "type": "text",
                    "text": {
                        "content": database_title
                    }
                }
            ],
            properties=database_properties
        )
        
        database_id = response["id"]
        print(f"✅ Successfully created database: {database_id}")
        print(f"\n📝 To use this database, update your config.py:")
        print(f'DATABASE_ID = "{database_id}"')
        
        return database_id
        
    except json.JSONDecodeError as e:
        print(f"❌ Invalid JSON in schema file: {e}")
        return None
    except Exception as e:
        print(f"❌ Error creating database: {e}")
        return None

def main():
    parser = argparse.ArgumentParser(
        description="Create a new Notion database with specified schema",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python3 create_notion_database.py --schema voice_memo_schema.json --page-id c319aa07d0204290afc396d0bbaee5e5

Schema file format:
  {
    "title": "Database Name",
    "properties": {
      "Title": {"title": {}},
      "Tags": {"rich_text": {}},
      ...
    }
  }
        """
    )
    
    parser.add_argument(
        "--schema",
        required=True,
        help="Path to JSON file containing database schema"
    )
    
    parser.add_argument(
        "--page-id", 
        required=True,
        help="Notion page ID where database should be created"
    )
    
    args = parser.parse_args()
    
    print("🚀 NOTION DATABASE CREATOR")
    print("=" * 50)
    
    database_id = createNotionDatabase(args.schema, args.page_id)
    
    if database_id:
        print("\n🎉 Database creation successful!")
        print(f"Database ID: {database_id}")
    else:
        print("\n💥 Database creation failed!")
        sys.exit(1)

if __name__ == "__main__":
    main()