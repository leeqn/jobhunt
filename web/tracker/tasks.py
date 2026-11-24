import asyncio
import logging
from celery import shared_task
from django.core.cache import cache
from parser.runner import run_scrapers

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=2, default_retry_delay=300)
def scrape_vacancies_task(self, query: str = "Python"):
    try:
        logger.info("Starting background scraping for query: %s", query)
        asyncio.run(run_scrapers(query=query))
        cache.clear()
        logger.info("Scraping for '%s' completed, Redis cache cleared.", query)
        return f"Done: {query}"
    except Exception as exc:
        logger.warning("Error scraping '%s': %s. Retrying...", query, exc)
        raise self.retry(exc=exc)
