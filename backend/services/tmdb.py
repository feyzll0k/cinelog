import os
import requests
from dotenv import load_dotenv

load_dotenv()

TMDB_API_KEY = os.getenv("TMDB_API_KEY")
TMDB_BASE_URL = os.getenv("TMDB_BASE_URL", "https://api.themoviedb.org/3")
TMDB_IMAGE_BASE_URL = "https://image.tmdb.org/t/p"


def _make_request(endpoint: str, params: dict = None) -> dict:
    """TMDB API'sine GET isteği atar, ortak parametreleri ve hata yönetimini sağlar."""
    if not TMDB_API_KEY:
        raise ValueError("TMDB_API_KEY bulunamadı. Lütfen .env dosyanızı kontrol edin.")

    url = f"{TMDB_BASE_URL.rstrip('/')}/{endpoint.lstrip('/')}"
    request_params = {
        "api_key": TMDB_API_KEY,
    }
    if params:
        request_params.update(params)

    try:
        response = requests.get(url, params=request_params, timeout=10)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.HTTPError as http_err:
        if response.status_code == 404:
            return None
        raise RuntimeError(f"TMDB API HTTP Hatası ({response.status_code}): {http_err}") from http_err
    except requests.exceptions.RequestException as req_err:
        raise RuntimeError(f"TMDB API Bağlantı Hatası: {req_err}") from req_err


def build_image_url(path: str, size: str = "w500") -> str:
    """
    TMDB görsel yolu için tam URL üretir.
    Boyut alternatifleri: 'w185', 'w342', 'w500', 'w780', 'original'
    """
    if not path:
        return None
    return f"{TMDB_IMAGE_BASE_URL}/{size}/{path.lstrip('/')}"


def search_movies(query: str, page: int = 1, language: str = "tr-TR") -> dict:
    """Film adına göre arama yapar."""
    if not query or not query.strip():
        return {"results": [], "total_results": 0, "total_pages": 0, "page": page}

    return _make_request(
        "search/movie",
        {"query": query.strip(), "page": page, "language": language},
    )


def get_popular_movies(page: int = 1, language: str = "tr-TR") -> dict:
    """Günün/haftanın popüler filmlerini listeler."""
    return _make_request(
        "movie/popular",
        {"page": page, "language": language},
    )


def get_top_rated_movies(page: int = 1, language: str = "tr-TR") -> dict:
    """En yüksek puanlı filmleri listeler."""
    return _make_request(
        "movie/top_rated",
        {"page": page, "language": language},
    )


def get_movie_details(tmdb_id: int, language: str = "tr-TR") -> dict:
    """Belirli bir filmin detay bilgilerini getirir."""
    return _make_request(f"movie/{tmdb_id}", {"language": language})


def get_movie_credits(tmdb_id: int, language: str = "tr-TR") -> dict:
    """Filmin oyuncu kadrosunu ve ekibini getirir."""
    return _make_request(f"movie/{tmdb_id}/credits", {"language": language})


def get_genres(language: str = "tr-TR") -> list:
    """Tüm resmi TMDB film türlerini getirir."""
    data = _make_request("genre/movie/list", {"language": language})
    return data.get("genres", []) if data else []

