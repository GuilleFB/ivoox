import logging
import re
from dataclasses import dataclass
from typing import Any
from urllib.parse import urljoin

import requests
from lxml import html

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


@dataclass
class Podcast:
    """Represents a podcast with its metadata."""

    id: str
    name: str
    ivoox_url: str
    thumbnail: str

    def to_dict(self) -> dict[str, str]:
        return {
            "id": self.id,
            "name": self.name,
            "ivoox_url": self.ivoox_url,
            "thumbnail": self.thumbnail,
        }


@dataclass
class Episode:
    """Represents an episode with its metadata."""

    name: str
    description: str
    url: str
    duration: str
    thumbnail: str
    likes: str
    comments: str

    def to_dict(self) -> dict[str, str]:
        return {
            "name": self.name,
            "description": self.description,
            "url": self.url,
            "duration": self.duration,
            "thumbnail": self.thumbnail,
            "likes": self.likes,
            "comments": self.comments,
        }


class IvooxAPI:
    """Client for scraping podcast data from Ivoox."""

    BASE_URL = "http://www.ivoox.com"
    REQUEST_TIMEOUT = 10
    PODCAST_ID_PATTERN = re.compile(r"_sq_(.*?)_1\.html")

    def __init__(self, timeout: int = REQUEST_TIMEOUT):
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            },
        )

    def search_podcast(
        self,
        query: str,
        page: int | None = None,
    ) -> list[dict[str, str]]:
        """
        Search for podcasts on Ivoox.

        Args:
            query: Search term
            page: Specific page number. If None, fetches all pages

        Returns:
            List of podcast dictionaries
        """
        results = []
        start_page = page if page is not None else 1
        current_page = start_page

        while True:
            url = f"{self.BASE_URL}/{query}_sw_1_{current_page}.html"
            logger.info(f"Searching: {url}")

            tree = self._fetch_and_parse(url)
            if tree is None:
                break

            podcasts = self._parse_podcast_nodes(tree)
            if not podcasts:
                break

            results.extend(podcast.to_dict() for podcast in podcasts)

            current_page += 1

        return results

    def search_episodes(
        self,
        podcast_id: str,
        page: int | None = None,
    ) -> dict[str, Any]:
        """
        Fetch episodes for a specific podcast.

        Args:
            podcast_id: Podcast ID from search_podcast()
            page: Specific page number. If None, fetches all pages

        Returns:
            Dictionary with podcast name and list of episodes
        """
        result = {"name": "", "episodes": []}
        start_page = page if page is not None else 1
        current_page = start_page

        while True:
            url = f"{self.BASE_URL}/test_sq_{podcast_id}_{current_page}.html"
            logger.info(f"Fetching episodes: {url}")

            tree = self._fetch_and_parse(url)
            if tree is None:
                break

            if not result["name"]:
                result["name"] = self._extract_podcast_name(tree, current_page)
                if not result["name"] and current_page == 1:
                    logger.error("Could not find podcast title. Invalid ID?")
                    break

            episodes = self._parse_episode_nodes(tree)
            if not episodes:
                break

            result["episodes"].extend(episode.to_dict() for episode in episodes)

            if page is not None or not self._has_next_page(tree):
                break

            current_page += 1

        return result

    def get_mp3_links(
        self,
        podcast_url: str,
        page: int | None = None,
    ) -> list[dict[str, str]]:
        """
        Extrae los enlaces MP3 directamente del listado de episodios.
        """
        all_mp3s = []
        base_url = re.sub(r"_\d+\.html$", "", podcast_url)
        start_page = page if page is not None else 1
        current_page = start_page

        while True:
            url = f"{base_url}_{current_page}.html"
            logger.info(f"\nObteniendo MP3s de página {current_page}: {url}")

            tree = self._fetch_and_parse(url)
            if tree is None:
                break

            # Buscar todos los enlaces con mp3_rf_
            episode_links = tree.xpath(
                "//a[contains(@href, 'mp3_rf_') and contains(@class, 'font-size-14 font-size-md-16')]",
            )
            episode_thumbnails = tree.xpath(
                "//img[contains(@src, 'img-static.ivoox.com') and contains(@class, 'img-hover img-rounded')]",
            )

            if not episode_links:
                logger.info("No hay más episodios")
                break

            for i in range(len(episode_links)):
                link = episode_links[i]
                thumbnail = episode_thumbnails[i]
                href = link.get("href", "")
                title = link.get("title") or link.text_content().strip()
                thumb_src = thumbnail.get("src", "")
                all_mp3s.append(
                    {
                        "title": title,
                        "mp3_url": self.construir_url_audio(self.BASE_URL + href),
                        "thumbnail": thumb_src,
                    },
                )

            logger.info(f"  ✓ {len(episode_links)} episodios en esta página")

            current_page += 1

        logger.info(f"\n✓ Total: {len(all_mp3s)} MP3s encontrados")
        return all_mp3s

    def construir_url_audio(self, url_original):
        """
        Extrae el número de referencia de la URL de iVoox y
        construye la URL de escucha directa.

        Args:
            url_original (str): La URL completa de iVoox
            (ej: 'http://www.ivoox.com/horizonte-t6x08-brutal-agresion-abertzales-a-periodista-audios-mp3_rf_161629863_1.html').

        Returns:
            str: La URL de escucha directa
            (ej: 'https://www.ivoox.com/listen_mn_161629863_1.mp3').
        """
        # Patrón de expresión regular para capturar la parte que deseas.
        # Busca '_rf_' seguido de uno o más dígitos, un guion bajo y otro dígito,
        # y lo captura en un grupo.
        patron = r"_rf_(\d+_\d+)\.html"

        # Buscar el patrón en la URL original
        coincidencia = re.search(patron, url_original)

        if coincidencia:
            # El grupo 1 contiene el número deseado (ej: '161629863_1')
            numero_referencia = coincidencia.group(1)

            # Construir la nueva URL
            return f"https://www.ivoox.com/listen_mn_{numero_referencia}.mp3"
        # Devolver un mensaje de error si no se encuentra el patrón
        return "Error: No se pudo extraer el número de referencia de la URL proporcionada."

    def _fetch_and_parse(self, url: str) -> html.HtmlElement | None:
        """Fetch URL and parse HTML, returning None on error."""
        try:
            response = self.session.get(url, timeout=self.timeout)
            response.raise_for_status()
            return html.fromstring(response.text)
        except requests.RequestException as e:
            logger.error(f"Failed to fetch {url}: {e}")
            return None

    def _parse_podcast_nodes(self, tree: html.HtmlElement) -> list[Podcast]:
        """Extract podcast data from parsed HTML."""
        podcasts = []
        nodes = tree.xpath("//div[@class='front modulo-view modulo-type-programa']")

        for node in nodes:
            try:
                link = node.xpath(".//a")[0]
                url = link.get("href", "")

                if "_sq_" not in url or url.startswith("_sq_"):
                    continue

                match = self.PODCAST_ID_PATTERN.search(url)
                if not match:
                    continue

                podcasts.append(
                    Podcast(
                        id=match.group(1),
                        name=link.get("title", ""),
                        ivoox_url=url,
                        thumbnail=node.xpath(".//img")[0].get("src", ""),
                    ),
                )
            except (IndexError, AttributeError) as e:
                logger.debug(f"Error parsing podcast node: {e}")
                continue

        return podcasts

    def _parse_episode_nodes(self, tree: html.HtmlElement) -> list[Episode]:
        """Extract episode data from parsed HTML."""
        episodes = []
        nodes = tree.xpath("//div[@class='front modulo-view modulo-type-episodio']")

        for node in nodes:
            try:
                title_wrapper = node.xpath(
                    ".//p[@class='title-wrapper text-ellipsis-multiple']",
                )[0]
                link = title_wrapper.xpath(".//a")[0]

                episodes.append(
                    Episode(
                        name=link.get("title", ""),
                        url=link.get("href", ""),
                        description=title_wrapper.xpath(".//button")[0].get(
                            "data-content",
                            "",
                        ),
                        thumbnail=node.xpath(".//div[@class='header-modulo']//img")[0].get("src", ""),
                        duration=node.xpath(".//p[@class='time']")[0].text_content().strip(),
                        likes=node.xpath(".//li[@class='likes']//a")[0].text_content().strip(),
                        comments=node.xpath(".//li[@class='comments']//a")[0].text_content().strip(),
                    ),
                )
            except (IndexError, AttributeError) as e:
                logger.debug(f"Error parsing episode node: {e}")
                continue

        return episodes

    def _extract_podcast_name(self, tree: html.HtmlElement, page: int) -> str:
        """Extract podcast name from page."""
        name_nodes = tree.xpath("//*[@id='list_title_new']")
        return name_nodes[0].text_content().strip() if name_nodes else ""

    def _extract_mp3_from_episode(
        self,
        link: html.HtmlElement,
    ) -> dict[str, str] | None:
        """Extract MP3 URL from episode page."""
        try:
            relative_url = link.get("href", "")
            title = link.text_content().strip()
            episode_url = urljoin(self.BASE_URL, relative_url)

            logger.info(f"  -> Scraping: {title[:50]}...")

            tree = self._fetch_and_parse(episode_url)
            if tree is None:
                return None

            # Intentar metodo 1: buscar en el objeto __NUXT__ (datos JSON embebidos)
            script_tags = tree.xpath("//script[contains(text(), 'mediaUrl')]")
            for script in script_tags:
                script_text = script.text_content()
                # Buscar el patrón del mediaUrl
                match = re.search(r'mediaUrl["\s:]+([^"\']+\.mp3)', script_text)
                if match:
                    mp3_url = match.group(1)
                    if not mp3_url.startswith("http"):
                        mp3_url = urljoin(self.BASE_URL, mp3_url)
                    return {"title": title, "mp3_url": mp3_url}

            # Metodo 2: buscar atributos data-src alternativos
            for attr in ["data-src-android", "data-src", "data-media-url"]:
                mp3_nodes = tree.xpath(f"//button[@{attr}] | //*[@{attr}]")
                if mp3_nodes:
                    relative_mp3 = mp3_nodes[0].get(attr, "")
                    if relative_mp3:
                        return {
                            "title": title,
                            "mp3_url": urljoin(self.BASE_URL, relative_mp3),
                        }

            logger.warning(f"     No MP3 found for '{title}'")
            return None

        except Exception:
            logger.exception("     Error extracting MP3")
            return None

    def _has_next_page(self, tree: html.HtmlElement) -> bool:
        """Check if pagination has a next page."""
        paginator_links = tree.xpath("//a[@class='page']//a")
        return paginator_links and paginator_links[-1].get("href") != "#"

    def _has_next_episode_page(self, tree: html.HtmlElement) -> bool:
        """Check if there's a next page for episodes."""
        next_links = tree.xpath(
            "//nav//a[not(contains(@class, 'disabled'))]//span[contains(text(), '')]",
        )
        return bool(next_links)

    def close(self):
        """Close the session."""
        self.session.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
