import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'top_repos.db')

def init_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS repos (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            owner TEXT NOT NULL,
            description TEXT,
            url TEXT NOT NULL,
            stars INTEGER NOT NULL,
            language TEXT,
            topics TEXT,
            updated_at TEXT
        )
    ''')
    conn.commit()
    return conn

def upsert_repos(repos_list):
    """
    Inserts or updates a list of repositories in the database.
    repos_list is a list of dictionaries.
    """
    conn = init_db()
    cursor = conn.cursor()
    
    for repo in repos_list:
        topics_str = ",".join(repo.get('topics', []))
        cursor.execute('''
            INSERT INTO repos (id, name, owner, description, url, stars, language, topics, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                name=excluded.name,
                owner=excluded.owner,
                description=excluded.description,
                url=excluded.url,
                stars=excluded.stars,
                language=excluded.language,
                topics=excluded.topics,
                updated_at=excluded.updated_at
        ''', (
            repo['id'],
            repo['name'],
            repo['owner'],
            repo.get('description', ''),
            repo['url'],
            repo['stars'],
            repo.get('language', ''),
            topics_str,
            repo.get('updated_at', '')
        ))
    
    conn.commit()
    conn.close()

def search_repos(keyword, limit=5):
    conn = init_db()
    cursor = conn.cursor()
    keyword = f"%{keyword}%"
    cursor.execute('''
        SELECT name, owner, description, url, stars, language, topics
        FROM repos
        WHERE name LIKE ? OR description LIKE ? OR topics LIKE ?
        ORDER BY stars DESC
        LIMIT ?
    ''', (keyword, keyword, keyword, limit))
    results = cursor.fetchall()
    conn.close()
    
    repos = []
    for r in results:
        repos.append({
            'name': r[0],
            'owner': r[1],
            'description': r[2],
            'url': r[3],
            'stars': r[4],
            'language': r[5],
            'topics': r[6]
        })
    return repos

def get_all_repos():
    conn = init_db()
    cursor = conn.cursor()
    cursor.execute('SELECT name, description, topics, url FROM repos')
    results = cursor.fetchall()
    conn.close()
    return results
