import logging

from celery import shared_task
from django.core.cache import cache

from .constants import CACHE_TTL_1M
from .constants import CACHE_TTL_24H
from .scraper import IvooxAPI

logger = logging.getLogger(__name__)


@shared_task(
    ignore_result=False,
)  # ignore_result=False es clave para guardar el resultado
def scrape_podcast_episodes_task(podcast_url):
    """
    Tarea de Celery que realiza el scraping de 10 minutos.
    El resultado (la lista de mp3_links) se guardará
    en el backend de resultados de Celery (Redis)
    Y también lo guardaremos en el caché de Django.
    """
    logger.info(f"[TAREA CELERY] Iniciando scraping para: {podcast_url}")

    # 1. Definir la clave de caché
    cache_key = f"episodes_view_{podcast_url}"

    try:
        with IvooxAPI() as api:
            # ¡EL TRABAJO PESADO DE 10 MINUTOS!
            mp3_links = api.get_mp3_links(podcast_url)

        # 2. Guardar en el caché de Django
        cache.set(cache_key, mp3_links, timeout=CACHE_TTL_24H)

        logger.info(f"[TAREA CELERY] Éxito. Guardado en caché: {cache_key}")

        # 3. Devolver el resultado
        # Celery guardará esto en el backend de resultados (Redis db 1)
        return mp3_links

    except Exception as e:
        logger.error(f"[TAREA CELERY] Error en scraping: {e}")
        # Cuando Celery ve una excepción, marca la tarea como 'FAILURE'
        raise


@shared_task(ignore_result=False)
def search_podcast_task(query):
    """
    Tarea de Celery que realiza el scraping de BÚSQUEDA.
    El resultado (la lista de podcasts) se guardará
    en el backend de resultados de Celery (Redis)
    Y también lo guardaremos en el caché de Django.
    """
    logger.info(f"[TAREA CELERY] Iniciando BÚSQUEDA para: {query}")

    # 1. Definir la clave de caché
    cache_key = f"search_view_{query.lower().replace(' ', '_')}"

    try:
        with IvooxAPI() as api:
            # ¡EL TRABAJO PESADO DE BÚSQUEDA!
            podcasts = api.search_podcast(query)

        # 2. Guardar en el caché de Django
        cache.set(cache_key, podcasts, timeout=CACHE_TTL_1M)

        logger.info(f"[TAREA CELERY] Éxito. Búsqueda guardada en caché: {cache_key}")

        # 3. Devolver el resultado
        return podcasts

    except Exception as e:
        logger.error(f"[TAREA CELERY] Error en scraping de búsqueda: {e}")
        # La tarea se marcará como 'FAILURE'
        raise
