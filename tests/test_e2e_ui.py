import pytest
import multiprocessing
import uvicorn
import time
import httpx
from playwright.sync_api import Page

from api.main import app

def run_server():
    uvicorn.run(app, host="127.0.0.1", port=8000, log_level="error")

@pytest.fixture(scope="session", autouse=True)
def start_server():
    proc = multiprocessing.Process(target=run_server, daemon=True)
    proc.start()
    
    # Wait for the server to be healthy
    for _ in range(30):
        try:
            resp = httpx.get("http://127.0.0.1:8000/")
            if resp.status_code == 200:
                break
        except Exception:
            pass
        time.sleep(0.5)
        
    yield
    proc.terminate()

def test_homepage_loads(page: Page):
    """Prueba que el frontend cargue y muestre WheelSaver."""
    page.goto("http://127.0.0.1:8000/")
    
    # Verificar titulo de la pagina
    assert "WheelSaver" in page.title()
    
    # Verificar que haya un input de busqueda
    search_input = page.locator("input#input-q")
    assert search_input.is_visible()

def test_search_ui_interaction(page: Page):
    """Prueba una interaccion basica en el frontend."""
    page.goto("http://127.0.0.1:8000/")
    
    search_input = page.locator("input#input-q")
    search_input.fill("test")
    
    # Simular 'Enter' para disparar la busqueda
    search_input.press("Enter")
    
    # Esperar a que cambie el DOM
    page.wait_for_selector("#results-card")
    results = page.locator("#results-card").inner_text()
    assert results is not None
