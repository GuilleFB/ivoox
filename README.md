# ivoox\_project 🎧

¡Bienvenido a `ivoox_project`\! Este es un potente scraper de podcasts construido con Django, diseñado para explorar el catálogo de Ivoox de forma eficiente y asíncrona.

¿Alguna vez has querido obtener todos los episodios de tu podcast favorito pero la tarea tarda demasiado? ¡Este proyecto lo soluciona\! 🚀

Busca un podcast, y la aplicación lanzará una tarea de Celery en segundo plano para hacer el trabajo pesado 🦾. Mientras tanto, la página te informará de que está trabajando y se recargará sola gracias a la magia del backend (¡sin necesidad de JavaScript\!). Cuando los resultados estén listos, se guardarán en caché para un acceso instantáneo.

Además, puedes guardar tus podcasts preferidos en tu perfil de usuario para no tener que buscarlos nunca más. ❤️

## ✨ Características Principales

  * **Búsqueda de Podcasts:** Busca en Ivoox usando el scraper integrado.
  * **Scraping Asíncrono:** Las búsquedas que tardan mucho se manejan con `Celery` para no bloquear al usuario.
  * **Página de Espera Automática:** Utiliza una recarga con `<meta http-equiv="refresh">` para comprobar el estado de la tarea, ofreciendo una experiencia de usuario fluida sin JS.
  * **Sistema de Favoritos:** Los usuarios pueden guardar y eliminar podcasts de su lista personal.
  * **Gestión de Usuarios:** Sistema completo de registro e inicio de sesión basado en email, cortesía de `django-allauth`.
  * **Cacheo Eficiente:** Los resultados de búsquedas y episodios se guardan en `Redis` para una carga casi instantánea en futuras visitas.
  * **100% Contenerizado:** Todo el entorno (Django, Postgres, Redis, Celery) está gestionado con `Docker Compose`.

## 🛠️ Stack Tecnológico

  * **Backend:** Django 5.2.7
  * **Python:** 3.13
  * **Base de Datos:** PostgreSQL
  * **Tareas Asíncronas:** Celery
  * **Broker / Caché:** Redis
  * **Entorno:** Docker & Docker Compose
  * **Testing:** `pytest`
  * **Linting/Formatting:** `Ruff` y `djLint`

-----

## 🚀 Cómo Empezar (Desarrollo Local)

Este proyecto está diseñado para funcionar con Docker Compose.

### 1\. Preparar el Entorno

1.  Clona este repositorio (o asegúrate de tener los archivos).
2.  Copia los archivos de entorno de ejemplo. Necesitarás:
      * `guillefb/ivoox/ivoox-develop/.envs/.local/.django`
      * `guillefb/ivoox/ivoox-develop/.envs/.local/.postgres`

### 2\. Levantar los Servicios

Construye las imágenes y levanta todos los contenedores (Django, Postgres, Redis, y los workers de Celery) en modo "detached":

```bash
docker compose -f docker-compose.local.yml up --build -d
```

### 3\. Preparar la Base de Datos

En otra terminal, ejecuta las migraciones de Django y crea tu cuenta de superusuario:

```bash
# Ejecutar migraciones (incluyendo la del modelo FavoritePodcast)
docker compose -f docker-compose.local.yml run --rm django python manage.py migrate

# Crear un superusuario para acceder
docker compose -f docker-compose.local.yml run --rm django python manage.py createsuperuser
```

### 4\. ¡Accede a la Aplicación\!

¡Eso es todo\! Ya puedes acceder a la aplicación en [http://localhost:8000](https://www.google.com/search?q=http://localhost:8000).

-----

## ⚙️ Servicios del Entorno

Al levantar `docker-compose.local.yml`, tendrás los siguientes servicios:

  * **`django`**: El servidor web de Django, visible en `http://localhost:8000`.
  * **`postgres`**: La base de datos PostgreSQL.
  * **`redis`**: El servidor de Redis, que maneja 3 bases de datos separadas:
      * **DB 0:** Bróker de Celery (cola de tareas).
      * **DB 1:** Backend de resultados de Celery.
      * **DB 2:** Caché de Django.
  * **`celeryworker`**: El worker que procesa las tareas de scraping.
  * **`celerybeat`**: El programador de tareas (para tareas periódicas).
  * **`flower`**: Un monitor para Celery, visible en `http://localhost:5555`.

## 🧪 Pruebas

Para ejecutar la suite de tests con `pytest`, usa el siguiente comando:

```bash
docker compose -f docker-compose.local.yml run --rm django pytest
```

-----

# ivoox\_project 🎧

Welcome to `ivoox_project`\! This is a powerful podcast scraper built with Django, designed to explore the Ivoox catalog efficiently and asynchronously.

Ever wanted to get all the episodes for your favorite podcast, but the task takes too long? This project solves that\! 🚀

Search for a podcast, and the application will launch a Celery background task to do the heavy lifting 🦾. Meanwhile, the page will notify you that it's working and will reload on its own thanks to some backend magic (no JavaScript required\!). When the results are ready, they'll be cached for instant access.

You can also save your favorite podcasts to your user profile so you never have to search for them again. ❤️

## ✨ Key Features

  * **Podcast Search:** Scrapes Ivoox using the built-in scraper.
  * **Asynchronous Scraping:** Long-running searches are handled by `Celery` to avoid blocking the user.
  * **No-JS Auto-Refresh:** Uses a `<meta http-equiv="refresh">` tag to check task status, providing a smooth user experience without JS.
  * **Favorites System:** Users can save and remove podcasts from their personal list.
  * **User Management:** Full email-based registration and login system, courtesy of `django-allauth`.
  * **Efficient Caching:** Search and episode results are cached in `Redis` for near-instant loading on future visits.
  * **100% Containerized:** The entire environment (Django, Postgres, Redis, Celery) is managed with `Docker Compose`.

## 🛠️ Tech Stack

  * **Backend:** Django 5.2.7
  * **Python:** 3.13
  * **Database:** PostgreSQL
  * **Async Tasks:** Celery
  * **Broker / Cache:** Redis
  * **Environment:** Docker & Docker Compose
  * **Testing:** `pytest`
  * **Linting/Formatting:** `Ruff` and `djLint`

-----

## 🚀 Getting Started (Local Development)

This project is designed to run with Docker Compose.

### 1\. Prepare Your Environment

1.  Clone this repository (or ensure you have the files).
2.  Copy the example environment files. You will need:
      * `guillefb/ivoox/ivoox-develop/.envs/.local/.django`
      * `guillefb/ivoox/ivoox-develop/.envs/.local/.postgres`

### 2\. Start the Services

Build the images and start all containers (Django, Postgres, Redis, and Celery workers) in detached mode:

```bash
docker compose -f docker-compose.local.yml up --build -d
```

### 3\. Set Up the Database

In another terminal, run the Django migrations and create your superuser account:

```bash
# Run migrations (including the FavoritePodcast model)
docker compose -f docker-compose.local.yml run --rm django python manage.py migrate

# Create a superuser to log in
docker compose -f docker-compose.local.yml run --rm django python manage.py createsuperuser
```

### 4\. Access the Application\!

That's it\! You can now access the application at [http://localhost:8000](https://www.google.com/search?q=http://localhost:8000).

-----

## ⚙️ Environment Services

When you run `docker-compose.local.yml`, you'll have the following services:

  * **`django`**: The Django web server, available at `http://localhost:8000`.
  * **`postgres`**: The PostgreSQL database.
  * **`redis`**: The Redis server, which handles 3 separate databases:
      * **DB 0:** Celery Broker (task queue).
      * **DB 1:** Celery Result Backend.
      * **DB 2:** Django Cache.
  * **`celeryworker`**: The worker that processes scraping tasks.
  * **`celerybeat`**: The task scheduler (for periodic tasks).
  * **`flower`**: A monitor for Celery, available at `http://localhost:5555`.

## 🧪 Testing

To run the `pytest` test suite, use the following command:

```bash
docker compose -f docker-compose.local.yml run --rm django pytest
```
