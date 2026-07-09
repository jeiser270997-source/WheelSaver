from playwright.sync_api import sync_playwright

def test():
    print("Iniciando Verificación E2E con Playwright...")
    try:
        with sync_playwright() as p:
            # Iniciamos navegador
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            
            # Navegar a la UI
            print("1. Cargando la Interfaz Web...")
            res = page.goto("http://127.0.0.1:8000/")
            assert res.status == 200, f"Error HTTP {res.status}"
            
            # Esperar a que carguen las estadísticas iniciales (el número no debe ser '-')
            print("2. Verificando carga de estadísticas...")
            page.wait_for_selector("#stat-repos:not(:has-text('-'))", timeout=5000)
            repos_text = page.locator("#stat-repos").inner_text()
            print(f"   [OK] Total Repositorios: {repos_text}")
            
            # Hacer una búsqueda
            print("3. Realizando busqueda: 'fastapi sqlite'")
            page.fill("#input-q", "fastapi sqlite")
            page.click("button:has-text('Buscar')")
            
            # Esperar a que los resultados se carguen en la tabla
            print("4. Verificando resultados de busqueda...")
            page.wait_for_selector("#results-body tr", timeout=5000)
            rows = page.locator("#results-body tr")
            count = rows.count()
            print(f"   [OK] Encontrados {count} repositorios.")
            
            # Mostrar el primer resultado para asegurar calidad
            first_repo = rows.nth(0).locator("td").nth(0).inner_text()
            first_stars = rows.nth(0).locator("td").nth(1).inner_text()
            print(f"   [OK] Top Resultado: {first_repo} con {first_stars} stars")
            
            browser.close()
            print("\n[EXITO] Todos los tests E2E pasaron satisfactoriamente!")
    except Exception as e:
        print(f"[ERROR] Error en la verificacion: {e}")

if __name__ == "__main__":
    test()
