import os
from celery import Celery
from scraper.github_fetcher import fetch_top_repos

REDIS_URL = os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0")

celery = Celery(
    __name__,
    broker=REDIS_URL,
    backend=REDIS_URL
)

@celery.task(name="worker.scrape_task")
def scrape_task(min_stars: int = 500):
    """
    Celery task that executes the GitHub scraper in a distributed background worker.
    """
    import logging
    logging.info(f"Iniciando Celery scraper con min_stars={min_stars}")
    try:
        fetch_top_repos(min_stars=min_stars)
        logging.info("Scraper finalizado con éxito.")
    except Exception as e:
        logging.error(f"Error en Celery scraper: {e}")
        raise e
