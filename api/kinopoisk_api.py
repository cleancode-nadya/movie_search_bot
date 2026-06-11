import requests
from config import API_KEY
from utils.logger import logger


class KinopoiskAPI:
    BASE_URL = "https://api.kinopoisk.dev/v1.4"

    def __init__(self):
        self.headers = {
            "X-API-KEY": API_KEY,
            "Content-Type": "application/json"
        }

    def search_movie(self, query: str, limit: int = 8, page: int = 1) -> dict:
        url = f"{self.BASE_URL}/movie/search"
        params = {"query": query, "limit": limit, "page": page}
        try:
            response = requests.get(url, headers=self.headers, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            return {
                "movies": [self._parse_movie(doc) for doc in data.get("docs", [])],
                "total":  data.get("total", 0),
                "pages":  data.get("pages", 1),
                "page":   data.get("page", 1),
            }
        except requests.exceptions.RequestException as e:
            logger.error(f"search_movie error: {e}")
            return {"movies": [], "total": 0, "pages": 1, "page": 1}

    def get_movie_details(self, movie_id: int) -> dict | None:
        url = f"{self.BASE_URL}/movie/{movie_id}"
        try:
            response = requests.get(url, headers=self.headers, timeout=10)
            response.raise_for_status()
            return self._parse_movie_full(response.json())
        except requests.exceptions.RequestException as e:
            logger.error(f"get_movie_details error: {e}")
            return None

    def _parse_movie(self, doc: dict) -> dict:
        return {
            "id":          doc.get("id"),
            "title":       doc.get("name") or doc.get("alternativeName") or "Без названия",
            "title_en":    doc.get("alternativeName", ""),
            "year":        doc.get("year"),
            "rating":      doc.get("rating", {}).get("kp"),
            "rating_imdb": doc.get("rating", {}).get("imdb"),
            "description": doc.get("description") or "",
            "poster":      doc.get("poster", {}).get("url"),
            "genres":      [g["name"] for g in doc.get("genres", [])],
            "type":        doc.get("type", "movie"),
        }

    def _parse_movie_full(self, doc: dict) -> dict:
        base = self._parse_movie(doc)
        base.update({
            "length":        doc.get("movieLength"),
            "countries":     [c["name"] for c in doc.get("countries", [])],
            "similarMovies": doc.get("similarMovies", [])[:5],
            "ageRating":     doc.get("ageRating"),
            "slogan":        doc.get("slogan") or "",
        })
        return base
