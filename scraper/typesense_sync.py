import sqlite3
import typesense
import os
import sys

# Asegurar path correcto
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

TYPESENSE_API_KEY = os.getenv("TYPESENSE_API_KEY", "wheelsaver_typesense_key")
TYPESENSE_HOST = os.getenv("TYPESENSE_HOST", "localhost")
DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "top_repos.db")

client = typesense.Client({
  'nodes': [{
    'host': TYPESENSE_HOST,
    'port': '8108',
    'protocol': 'http'
  }],
  'api_key': TYPESENSE_API_KEY,
  'connection_timeout_seconds': 5
})

def sync_db():
    print("Sincronizando SQLite a Typesense...")
    
    schema = {
        'name': 'repos',
        'fields': [
            {'name': 'name', 'type': 'string'},
            {'name': 'owner', 'type': 'string'},
            {'name': 'description', 'type': 'string', 'optional': True},
            {'name': 'language', 'type': 'string', 'optional': True, 'facet': True},
            {'name': 'stars', 'type': 'int32'},
            {'name': 'topics', 'type': 'string', 'optional': True},
            {'name': 'url', 'type': 'string'}
        ],
        'default_sorting_field': 'stars'
    }
    
    try:
        client.collections['repos'].delete()
    except Exception:
        pass
        
    client.collections.create(schema)

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM repos")
    rows = cursor.fetchall()

    documents = []
    for row in rows:
        documents.append({
            'id': str(row['id']),
            'name': row['name'],
            'owner': row['owner'],
            'description': row['description'] or "",
            'language': row['language'] or "",
            'stars': row['stars'],
            'topics': row['topics'] or "",
            'url': row['url']
        })

    if documents:
        # Importar en lotes
        client.collections['repos'].documents.import_(documents, {'action': 'create'})
        
    print(f"✅ Sincronizados {len(documents)} repositorios a Typesense.")

if __name__ == "__main__":
    sync_db()
