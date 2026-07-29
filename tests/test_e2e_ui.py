import pytest
import threading
import uvicorn
import time
import httpx
from playwright.sync_api import Page

from api.main import app

import socket

def get_free_port():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(('127.0.0.1', 0))
        return s.getsockname()[1]

TEST_PORT = get_free_port()

class ServerThread(threading.Thread):
    def __init__(self):
        super().__init__(daemon=True)
        self.server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=TEST_PORT, log_level="error"))

    def run(self):
        self.server.run()

    def stop(self):
        self.server.should_exit = True

@pytest.fixture(scope="session", autouse=True)
def start_server():
    server = ServerThread()
    server.start()
    
    # Wait for the server to be healthy
    for _ in range(30):
        try:
            resp = httpx.get(f"http://127.0.0.1:{TEST_PORT}/health")
            if resp.status_code == 200:
                break
        except Exception:
            pass
        time.sleep(0.2)
        
    yield
    server.stop()

def test_homepage_loads(page: Page):
    """Prueba que el frontend cargue y muestre WheelSaver."""
    page.goto(f"http://127.0.0.1:{TEST_PORT}/web/index.html")
    
    # Verificar titulo de la pagina
    assert "WheelSaver" in page.title()
    
    # Verificar que haya un input de busqueda
    search_input = page.locator("input#input-q")
    assert search_input.is_visible()

def test_search_ui_interaction(page: Page):
    """Prueba una interaccion basica en el frontend."""
    page.goto(f"http://127.0.0.1:{TEST_PORT}/web/index.html")
    
    search_input = page.locator("input#input-q")
    search_input.fill("test")
    
    # Simular 'Enter' para disparar la busqueda
    search_input.press("Enter")
    
    # Esperar a que cambie el DOM
    page.wait_for_selector("#results-card", timeout=5000)
    results = page.locator("#results-card").inner_text()
    assert results is not None
