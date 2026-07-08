import os
import requests
import time
from dotenv import load_dotenv
from scraper.db_manager import upsert_repos

load_dotenv(override=True)

GITHUB_TOKEN = os.getenv('GITHUB_TOKEN')

def fetch_top_repos(target_count=10000):
    if not GITHUB_TOKEN:
        print("Error: GITHUB_TOKEN no encontrado en .env")
        return

    url = 'https://api.github.com/graphql'
    headers = {
        'Authorization': f'Bearer {GITHUB_TOKEN}',
        'Content-Type': 'application/json',
    }

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

    total_fetched = 0
    # Empezamos buscando desde un número ridículamente alto hacia abajo
    current_max_stars = 9999999 

    print(f"Iniciando descarga masiva de {target_count} repositorios en tramos seguros...")

    while total_fetched < target_count:
        # Buscamos repositorios con menos o igual estrellas que nuestro límite actual
        query_string = f"stars:<={current_max_stars} sort:stars-desc"
        cursor = None
        has_next_page = True
        
        # En cada query_string (cada tramo), GitHub nos dará hasta 1000 resultados (10 páginas de 100)
        fetched_in_this_range = 0
        last_repo_stars = current_max_stars

        while has_next_page and total_fetched < target_count:
            variables = {
                "queryString": query_string,
                "cursor": cursor
            }

            response = requests.post(url, headers=headers, json={'query': query, 'variables': variables})
            
            if response.status_code == 200:
                data = response.json()
                if 'errors' in data:
                    print(f"Error en GraphQL: {data['errors']}")
                    # Si falla, esperamos y rompemos el ciclo interno para reintentar o bajar el max_stars
                    time.sleep(5)
                    break
                    
                search_data = data['data']['search']
                edges = search_data['edges']
                page_info = search_data['pageInfo']
                
                if not edges:
                    break # No hay más resultados en este tramo

                repos_to_insert = []
                for edge in edges:
                    node = edge['node']
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
                    last_repo_stars = node['stargazerCount']
                
                upsert_repos(repos_to_insert)
                total_fetched += len(repos_to_insert)
                fetched_in_this_range += len(repos_to_insert)
                
                print(f"Progreso Total: {total_fetched}/{target_count} repos (Último procesado: {last_repo_stars} estrellas)")
                
                has_next_page = page_info['hasNextPage']
                cursor = page_info['endCursor']
                
                # Pequeña pausa para respetar rate limits de la API
                time.sleep(0.5)
            else:
                print(f"Fallo en la petición: {response.status_code} - {response.text}")
                time.sleep(10)
                break

        # Cuando terminamos un tramo (porque llegamos al límite de 1000 de GitHub para esa búsqueda),
        # actualizamos nuestro límite superior de estrellas para la siguiente búsqueda.
        # Restamos 1 estrella al último procesado para evitar un bucle infinito atrapado en los mismos repos.
        if last_repo_stars < current_max_stars:
            current_max_stars = last_repo_stars - 1
        else:
            # Si por alguna razón extraña todos los 1000 repos tenían exactamente la misma cantidad de estrellas
            current_max_stars -= 1

        if current_max_stars < 50:
            print("Se ha llegado a repositorios con muy pocas estrellas. Finalizando.")
            break

    print("¡Descarga masiva finalizada con éxito!")

if __name__ == "__main__":
    fetch_top_repos()
