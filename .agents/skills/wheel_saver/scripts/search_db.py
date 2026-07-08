import sqlite3
import sys
import os
import json

def search_db(keywords):
    # .agents/skills/wheel_saver/scripts/search_db.py -> subir 5 niveles para llegar a la raiz del proyecto
    root_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))
    db_path = os.path.join(root_dir, 'data', 'top_repos.db')

    if not os.path.exists(db_path):
        print(json.dumps({"error": f"Base de datos no encontrada en {db_path}"}))
        return

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    results_dict = {}

    for kw in keywords:
        try:
            cursor.execute('''
                SELECT r.name, r.owner, r.description, r.url, r.stars, r.language, r.topics
                FROM repos_fts f
                JOIN repos r ON r.rowid = f.rowid
                WHERE repos_fts MATCH ?
                ORDER BY r.stars DESC
                LIMIT 15
            ''', (kw,))
        except sqlite3.OperationalError:
            like_kw = f"%{kw}%"
            cursor.execute('''
                SELECT name, owner, description, url, stars, language, topics
                FROM repos
                WHERE name LIKE ? OR description LIKE ? OR topics LIKE ?
                ORDER BY stars DESC
                LIMIT 15
            ''', (like_kw, like_kw, like_kw))

        for row in cursor.fetchall():
            name = row[0]
            if name not in results_dict:
                results_dict[name] = {
                    'name': row[0],
                    'owner': row[1],
                    'description': row[2],
                    'url': row[3],
                    'stars': row[4],
                    'language': row[5],
                    'topics': row[6].split(',') if row[6] else []
                }

    conn.close()
    sorted_results = sorted(list(results_dict.values()), key=lambda x: x['stars'], reverse=True)
    print(json.dumps(sorted_results[:25], indent=2))

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(json.dumps({"error": "Faltan keywords. Uso: python search_db.py keyword1 keyword2 ..."}))
    else:
        search_db(sys.argv[1:])
