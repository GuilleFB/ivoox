from django.urls import path

from .views import EpisodeDataView
from .views import EpisodesView
from .views import SearchDataView
from .views import SearchView
from .views import TaskStatusView

urlpatterns = [
    path("search/", SearchView.as_view(), name="search"),
    path("episodes/", EpisodesView.as_view(), name="episodes"),
    path("api/search-data/", SearchDataView.as_view(), name="api_search_data"),
    path("api/episodes-data/", EpisodeDataView.as_view(), name="api_episodes_data"),
    path("api/task-status/", TaskStatusView.as_view(), name="api_task_status"),
]
