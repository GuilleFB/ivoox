from django.urls import path

from .views import EpisodeDataView, EpisodesView, FavoriteListView, SearchView, TaskStatusView, ToggleFavoriteView

urlpatterns = [
    path("search/", SearchView.as_view(), name="search"),
    path("episodes/", EpisodesView.as_view(), name="episodes"),
    path("favorites/", FavoriteListView.as_view(), name="favorites"),
    path("api/episodes-data/", EpisodeDataView.as_view(), name="api_episodes_data"),
    path("api/task-status/", TaskStatusView.as_view(), name="api_task_status"),
    path("toggle-favorite/", ToggleFavoriteView.as_view(), name="toggle_favorite"),
]
