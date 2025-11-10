# Create your models here.
from django.conf import settings
from django.db import models


class FavoritePodcast(models.Model):
    """
    Guarda la relación entre un Usuario y un Podcast que ha marcado
    como favorito.
    """

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="favorites")
    # Usamos el ID de Ivoox (que ya tenías en el scraper)
    # como identificador único del podcast
    ivoox_id = models.CharField(max_length=100, db_index=True)

    # Guardamos los datos del podcast para mostrarlos en la lista
    # de favoritos sin tener que volver a scrapear.
    name = models.CharField(max_length=255)
    ivoox_url = models.URLField(max_length=1024)
    thumbnail_url = models.URLField(max_length=1024)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        # Un usuario no puede tener el mismo podcast dos veces
        unique_together = ("user", "ivoox_id")
        ordering = ["-created_at"]

    def __str__(self):
        return f"'{self.name}' (Favorito de {self.user.email})"
