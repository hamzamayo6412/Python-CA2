"""Orchestrate fetching, processing, and model training with safe fallbacks."""

from app.api import RapidAPIError, fetch_and_cache_movies, load_cached_movies
from app.data_processor import CLEAN_MOVIES_PATH, process_movies
from app.recommender import RECOMMENDER_PATH, train_and_save


DEFAULT_GENRES = ["Action", "Drama", "Comedy", "Sci-Fi", "Horror"]


def refresh_all_data(genres=None, pages_per_genre=1, rows=10):
    """Refresh movie data end-to-end. Falls back to cached raw data if the API fails."""
    genres = genres or DEFAULT_GENRES
    used_cache_fallback = False
    refresh_error = None
    movie_count = 0

    try:
        payload = fetch_and_cache_movies(
            genres=genres,
            pages_per_genre=pages_per_genre,
            rows=rows,
            fallback_to_cache=True,
        )
        movie_count = payload.get("meta", {}).get("movie_count", 0)
        used_cache_fallback = payload.get("meta", {}).get("used_cache_fallback", False)
        refresh_error = payload.get("meta", {}).get("refresh_error")
    except RapidAPIError as error:
        cached = load_cached_movies()
        movie_count = len(cached.get("movies", []))
        used_cache_fallback = True
        refresh_error = str(error)

        if movie_count == 0:
            raise

    process_movies()
    recommender = train_and_save()

    return {
        "movie_count": movie_count,
        "clean_csv": str(CLEAN_MOVIES_PATH),
        "model_path": str(RECOMMENDER_PATH),
        "used_cache_fallback": used_cache_fallback,
        "refresh_error": refresh_error,
        "recommender_movie_count": len(recommender.movies_df),
    }


def reload_app_data(app):
    """Reload in-memory movie data and recommender after a refresh."""
    from app.data_processor import load_clean_movies
    from app.recommender import get_recommender

    app.config["MOVIES_DF"] = load_clean_movies()
    app.config["RECOMMENDER"] = get_recommender(reload=True)
