import logging

from celery.result import AsyncResult
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.cache import cache
from django.http import HttpResponseBadRequest, JsonResponse
from django.shortcuts import redirect
from django.views.generic import ListView, TemplateView, View

from .models import FavoritePodcast
from .tasks import scrape_podcast_episodes_task, search_podcast_task

logger = logging.getLogger(__name__)


class SearchView(LoginRequiredMixin, TemplateView):
    """
    Página principal con el buscador.
    ¡Ahora maneja TODA la lógica de búsqueda, caché y tareas!
    """

    template_name = "pages/search.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        request = self.request
        query = request.GET.get("query", "").strip()
        context["query"] = query

        if not query:
            # Si no hay búsqueda, simplemente muestra la página vacía
            return context

        # 1. Definir claves
        cache_key = f"search_view_{query.lower().replace(' ', '_')}"
        task_cache_key = f"task_id_for_search_{query}"

        # 2. Intentar obtener datos del caché de Django
        cached_data = cache.get(cache_key)
        if cached_data:
            logger.info(f"Cache HIT para búsqueda: {query}")
            context["podcasts"] = cached_data
            # También obtenemos los IDs de los favoritos del usuario
            context["user_favorites_ids"] = set(
                FavoritePodcast.objects.filter(user=request.user).values_list("ivoox_id", flat=True),
            )
            return context

        # 3. ¡Cache MISS! Revisar si hay una tarea en curso
        task_id = cache.get(task_cache_key)
        if task_id:
            task = AsyncResult(task_id)

            if task.state == "SUCCESS":
                # La tarea terminó, guardamos el resultado y lo mostramos
                logger.info(f"Tarea {task_id} terminada. Obteniendo resultados.")
                podcasts = task.result
                context["podcasts"] = podcasts
                context["user_favorites_ids"] = set(
                    FavoritePodcast.objects.filter(user=request.user).values_list("ivoox_id", flat=True),
                )
                cache.delete(task_cache_key)  # Limpiamos el ID de la tarea
                return context

            if task.state in ("PENDING", "PROCESSING", "STARTED"):
                # La tarea sigue en curso. Informamos a la plantilla.
                logger.info(f"Tarea {task_id} sigue en proceso...")
                context["task_id"] = task_id
                return context

            if task.state == "FAILURE":
                logger.error(f"Tarea {task_id} falló.")
                context["error_message"] = "La tarea de búsqueda falló en el servidor."
                cache.delete(task_cache_key)  # Limpiamos la tarea fallida
                return context

        # 4. No hay caché Y no hay tarea en curso. Lanzamos una nueva.
        logger.info(f"Cache MISS para búsqueda. Lanzando tarea Celery para: {query}")
        task = search_podcast_task.delay(query)

        # Guardamos el ID de la tarea en caché para la próxima recarga
        cache.set(task_cache_key, task.id, timeout=600)  # 10 min

        context["task_id"] = task.id  # Informamos a la plantilla
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


class FavoriteListView(LoginRequiredMixin, ListView):
    """
    Muestra la lista de podcasts favoritos del usuario logueado.
    """

    model = FavoritePodcast
    template_name = "pages/favorites.html"
    context_object_name = "favorite_list"

    def get_queryset(self):
        # Filtra los favoritos solo para el usuario actual
        return FavoritePodcast.objects.filter(user=self.request.user).order_by("-created_at")


class ToggleFavoriteView(LoginRequiredMixin, View):
    """
    Vista que maneja un <form> POST para añadir o quitar un favorito.
    NO es una API de JSON, es una vista de Django normal.
    """

    def post(self, request, *args, **kwargs):
        # Obtenemos los datos del formulario que envió el navegador
        data = request.POST
        ivoox_id = data.get("ivoox_id")

        if not ivoox_id:
            return HttpResponseBadRequest("Falta 'ivoox_id'")

        # Intentamos encontrar el favorito
        favorite, created = FavoritePodcast.objects.get_or_create(
            user=request.user,
            ivoox_id=ivoox_id,
            defaults={
                "name": data.get("name"),
                "ivoox_url": data.get("ivoox_url"),
                "thumbnail_url": data.get("thumbnail_url"),
            },
        )

        if not created:
            # Si no fue creado, ya existía. Lo borramos.
            favorite.delete()
            logger.info(f"Favorito eliminado: {data.get('name')}")
        else:
            logger.info(f"Favorito añadido: {favorite.name}")

        # MUY IMPORTANTE: Redirigimos al usuario a la página
        # exacta desde la que vino (ej. la página de búsqueda).
        return redirect(request.headers.get("referer", "search"))
