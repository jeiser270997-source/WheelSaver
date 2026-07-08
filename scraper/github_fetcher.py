import os
import requests
import time
from dotenv import load_dotenv
from scraper.db_manager import upsert_repos

load_dotenv()

GITHUB_TOKEN = os.getenv('GITHUB_TOKEN')

def fetch_top_repos(min_stars=500):
    if not GITHUB_TOKEN:
        print("Error: GITHUB_TOKEN no encontrado en .env")
        return

    url = 'https://api.github.com/graphql'
    headers = {
        'Authorization': f'Bearer {GITHUB_TOKEN}',
        'Content-Type': 'application/json',
    }

    # GraphQL query to get top repositories
    # We use the search endpoint in GraphQL
    query = """
    query($queryString: String!, $cursor: String) {
      search(query: $queryString, type: REPOSITORY, first: 100, after: $cursor) {
        pageInfo {
          endCursor
          hasNextPage
        }
        edges {
          node {
            ... on Repository {
              id
              name
              owner {
                login
              }
              description
              url
              stargazerCount
              primaryLanguage {
                name
              }
              repositoryTopics(first: 10) {
                nodes {
                  topic {
                    name
                  }
                }
              }
              updatedAt
            }
          }
        }
      }
    }
    """

    cursor = None
    has_next_page = True
    total_fetched = 0

    print(f"Iniciando descarga de repositorios con más de {min_stars} estrellas...")

    # Debido a límites de la API, podemos hacer búsquedas en bloques de estrellas si son muchos,
    # pero como prueba inicial, buscaremos los top sin importar el número.
    # En un escenario real, buscaríamos `stars:>500 sort:stars-desc`
    query_string = f"stars:>{min_stars} sort:stars-desc"

    while has_next_page:
        variables = {
            "queryString": query_string,
            "cursor": cursor
        }

        response = requests.post(url, headers=headers, json={'query': query, 'variables': variables})
        
        if response.status_code == 200:
            data = response.json()
            if 'errors' in data:
                print(f"Error en GraphQL: {data['errors']}")
                break
                
            search_data = data['data']['search']
            edges = search_data['edges']
            page_info = search_data['pageInfo']
            
            repos_to_insert = []
            for edge in edges:
                node = edge['node']
                # Procesar tags/topics
                topics = [t['topic']['name'] for t in node.get('repositoryTopics', {}).get('nodes', [])] if node.get('repositoryTopics') else []
                language = node.get('primaryLanguage', {})
                language_name = language.get('name', '') if language else ''
                
                repo_data = {
                    'id': node['id'],
                    'name': node['name'],
                    'owner': node['owner']['login'],
                    'description': node['description'],
                    'url': node['url'],
                    'stars': node['stargazerCount'],
                    'language': language_name,
                    'topics': topics,
                    'updated_at': node['updatedAt']
                }
                repos_to_insert.append(repo_data)
            
            upsert_repos(repos_to_insert)
            total_fetched += len(repos_to_insert)
            print(f"Descargados y guardados {total_fetched} repositorios...")
            
            has_next_page = page_info['hasNextPage']
            cursor = page_info['endCursor']
            
            # Respetar rate limits
            time.sleep(1)
            
            # Para evitar que el proceso tarde horas en la prueba inicial, podemos poner un límite artificial
            # Si el usuario quiere todos, se elimina este break.
            if total_fetched >= 1000: # Límite de prueba de 1000 repos
                print("Límite de prueba de 1000 repositorios alcanzado (puedes cambiar esto en el código).")
                break
        else:
            print(f"Fallo en la petición: {response.status_code} - {response.text}")
            # Considerar retry logic o rate limit wait (Retry-After)
            break

if __name__ == "__main__":
    fetch_top_repos()
