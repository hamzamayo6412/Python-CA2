import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path

import requests
from dotenv import load_dotenv

load_dotenv()

BASE_URL = "https://imdb236.p.rapidapi.com/api/imdb"
DEFAULT_HOST = "imdb236.p.rapidapi.com"
DATA_DIR = Path(__file__).resolve().parent.parent / "data"
RAW_MOVIES_PATH = DATA_DIR / "movies_raw.json"
REQUEST_DELAY_SECONDS = 0.3


class RapidAPIError(Exception):
    """Raised when a RapidAPI request fails."""


def _get_api_key():
    api_key = os.getenv("RAPIDAPI_KEY", "").strip()
    if not api_key or api_key == "your_rapidapi_key_here":
        raise RapidAPIError(
            "RAPIDAPI_KEY is missing. Add your key to .env before fetching movies."
        )
    return api_key


def _get_headers():
    return {
        "x-rapidapi-key": _get_api_key(),
        "x-rapidapi-host": os.getenv("RAPIDAPI_HOST", DEFAULT_HOST).strip()
        or DEFAULT_HOST,
    }


def _request(endpoint, params=None):
    url = f"{BASE_URL}/{endpoint.lstrip('/')}"
    response = requests.get(url, headers=_get_headers(), params=params, timeout=30)

    if response.status_code != 200:
        raise RapidAPIError(
            f"Request failed ({response.status_code}) for {url}: {response.text[:200]}"
        )

    return response.json()


def fetch_movies(genre=None, page=1, rows=25):
    """Fetch a page of movies, optionally filtered by genre."""
    page = max(page, 1)
    rows = max(rows, 1)
    start = (page - 1) * rows

    if genre:
        params = {
            "type": "movie",
            "genre": genre,
            "rows": rows,
            "start": start,
            "sortOrder": "DESC",
            "sortField": "averageRating",
        }
        return _request("search", params=params)

    params = {"start": start} if start else None
    return _request("most-popular-movies", params=params)


def fetch_movie_details(movie_id):
    """Fetch full details for a single movie by IMDb ID."""
    movie_id = str(movie_id).strip()
    if not movie_id:
        raise ValueError("movie_id is required")

    return _request(movie_id)


def _extract_movie_ids(list_response):
    if isinstance(list_response, list):
        movies = list_response
    elif isinstance(list_response, dict):
        movies = list_response.get("results") or list_response.get("movies") or []
        if not movies and list_response.get("id"):
            movies = [list_response]
    else:
        movies = []

    movie_ids = []
    for movie in movies:
        if not isinstance(movie, dict):
            continue
        movie_id = movie.get("id") or movie.get("imdbId") or movie.get("imdb_id")
        if movie_id:
            movie_ids.append(str(movie_id))

    return movie_ids


def fetch_and_cache_movies(
    genres=None,
    pages_per_genre=1,
    rows=25,
    output_path=RAW_MOVIES_PATH,
):
    """Fetch movie lists and details, then save the raw API responses to JSON."""
    genres = genres or [None]
    cached_movies = []
    seen_ids = set()

    for genre in genres:
        for page in range(1, pages_per_genre + 1):
            list_response = fetch_movies(genre=genre, page=page, rows=rows)
            movie_ids = _extract_movie_ids(list_response)

            for movie_id in movie_ids:
                if movie_id in seen_ids:
                    continue

                seen_ids.add(movie_id)
                details = fetch_movie_details(movie_id)
                cached_movies.append(
                    {
                        "id": movie_id,
                        "genre_query": genre,
                        "list_data": _find_movie_in_list(list_response, movie_id),
                        "details": details,
                    }
                )
                time.sleep(REQUEST_DELAY_SECONDS)

            time.sleep(REQUEST_DELAY_SECONDS)

    payload = {
        "meta": {
            "fetched_at": datetime.now(timezone.utc).isoformat(),
            "source": "imdb236",
            "genres": genres,
            "pages_per_genre": pages_per_genre,
            "rows": rows,
            "movie_count": len(cached_movies),
        },
        "movies": cached_movies,
    }

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as file:
        json.dump(payload, file, indent=2)

    return payload


def _find_movie_in_list(list_response, movie_id):
    if isinstance(list_response, list):
        movies = list_response
    elif isinstance(list_response, dict):
        movies = list_response.get("results") or list_response.get("movies") or []
    else:
        return {}

    for movie in movies:
        if not isinstance(movie, dict):
            continue
        current_id = movie.get("id") or movie.get("imdbId") or movie.get("imdb_id")
        if str(current_id) == str(movie_id):
            return movie

    return {}


def load_cached_movies(path=RAW_MOVIES_PATH):
    """Load previously cached raw movie data from disk."""
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Cached movie file not found: {path}")

    with path.open(encoding="utf-8") as file:
        return json.load(file)


if __name__ == "__main__":
    genres = ["Action", "Drama", "Comedy", "Sci-Fi", "Horror"]
    result = fetch_and_cache_movies(genres=genres, pages_per_genre=1, rows=10)
    print(f"Cached {result['meta']['movie_count']} movies to {RAW_MOVIES_PATH}")
