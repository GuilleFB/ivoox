import logging

from celery.result import AsyncResult
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.cache import cache
from django.http import JsonResponse
from django.shortcuts import redirect
from django.views.generic import TemplateView
from django.views.generic import View

from .tasks import scrape_podcast_episodes_task
from .tasks import search_podcast_task

logger = logging.getLogger(__name__)


class SearchView(LoginRequiredMixin, TemplateView):
    """
    Página principal con el buscador (versión CBV).
    Muestra el formulario INMEDIATAMENTE.
    Si hay una consulta (query), el JS se encargará de
    lanzar la búsqueda asíncrona.
    """

    template_name = "pages/search.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Solo pasamos el 'query' al template.
        # El JS lo leerá para iniciar la búsqueda.
        context["query"] = self.request.GET.get("query", "")
        return context


class SearchDataView(LoginRequiredMixin, View):
    """
    API de AJAX: Revisa la caché de BÚSQUEDA y, si falla,
    LANZA UNA TAREA EN SEGUNDO PLANO.
    """

    def get(self, request, *args, **kwargs):
        query = request.GET.get("query")
        if not query:
            return JsonResponse(
                {"status": "ERROR", "message": "No se proporcionó 'query'"},
                status=400,
            )

        # 1. Definir la clave de caché
        cache_key = f"search_view_{query.lower().replace(' ', '_')}"

        # 2. Intentar obtener datos del caché
        cached_data = cache.get(cache_key)

        if cached_data:
            # 3. ¡Cache HIT! Devolvemos los datos inmediatamente
            logger.info(f"Cache HIT para búsqueda: {query}")
            return JsonResponse({"status": "SUCCESS", "data": cached_data})

        # 4. ¡Cache MISS!
        # Lanzamos la tarea de Celery en segundo plano.
        logger.info(f"Cache MISS para búsqueda. Lanzando tarea Celery para: {query}")
        task = search_podcast_task.delay(query)

        # 5. Devolvemos el ID de la tarea (el "ticket")
        return JsonResponse({"status": "PROCESSING", "task_id": task.id})


class EpisodesView(LoginRequiredMixin, TemplateView):
    """
    Muestra la plantilla de episodios INMEDIATAMENTE.
    El contenido se cargará vía AJAX.
    """

    template_name = "pages/episodes.html"

    def get(self, request, *args, **kwargs):
        if not request.GET.get("url"):
            return redirect("search")
        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["podcast_name"] = self.request.GET.get("name", "Podcast")
        context["podcast_url"] = self.request.GET.get("url")
        return context


class EpisodeDataView(LoginRequiredMixin, View):
    """
    API de AJAX: Revisa la caché y, si falla,
    LANZA UNA TAREA EN SEGUNDO PLANO.
    """

    def get(self, request, *args, **kwargs):
        podcast_url = request.GET.get("url")
        if not podcast_url:
            return JsonResponse(
                {"status": "ERROR", "message": "No se proporcionó URL"},
                status=400,
            )

        # 1. Definir la clave de caché
        cache_key = f"episodes_view_{podcast_url}"

        # 2. Intentar obtener datos del caché
        cached_data = cache.get(cache_key)

        if cached_data:
            # 3. ¡Cache HIT! Devolvemos los datos inmediatamente
            logger.info(f"Cache HIT para episodios: {podcast_url}")
            return JsonResponse({"status": "SUCCESS", "data": cached_data})

        # 4. ¡Cache MISS!
        # ¡NO HACEMOS SCRAPING!
        # Lanzamos la tarea de Celery en segundo plano.
        logger.info(
            f"Cache MISS para episodios. Lanzando tarea Celery para: {podcast_url}",
        )

        # .delay() ejecuta la tarea en el worker
        task = scrape_podcast_episodes_task.delay(podcast_url)

        # 5. Devolvemos el ID de la tarea (el "ticket")
        return JsonResponse({"status": "PROCESSING", "task_id": task.id})


class TaskStatusView(LoginRequiredMixin, View):
    """
    ¡NUEVA VISTA!
    El frontend vigilará (poll) esta vista para saber
    cuándo ha terminado la tarea.
    """

    def get(self, request, *args, **kwargs):
        task_id = request.GET.get("task_id")
        if not task_id:
            return JsonResponse(
                {"status": "ERROR", "message": "No se proporcionó task_id"},
                status=400,
            )

        # 1. Obtenemos el estado de la tarea desde el backend de Celery (Redis)
        task = AsyncResult(task_id)

        # 2. Comprobamos el estado
        if task.state == "SUCCESS":
            # ¡La tarea ha terminado!
            return JsonResponse(
                {
                    "status": "SUCCESS",
                    "data": task.result,  # Obtenemos el resultado (la lista de mp3_links)
                },
            )
        if task.state == "FAILURE":
            # La tarea ha fallado
            return JsonResponse(
                {
                    "status": "ERROR",
                    "message": "La tarea de scraping ha fallado.",
                },
            )
        # La tarea sigue en 'PENDING' o 'STARTED'
        return JsonResponse(
            {
                "status": "PROCESSING",
                "message": f"Estado de la tarea: {task.state}",
            },
        )
