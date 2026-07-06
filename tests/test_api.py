import json
from unittest.mock import patch

import pytest

from app.api import RAW_MOVIES_PATH, RapidAPIError, fetch_and_cache_movies, load_cached_movies


@pytest.fixture
def cached_payload(tmp_path):
    payload = {
        "meta": {"movie_count": 1, "source": "imdb236"},
        "movies": [
            {
                "id": "tt0111161",
                "genre_query": "Drama",
                "list_data": {"primaryTitle": "The Shawshank Redemption"},
                "details": {"primaryTitle": "The Shawshank Redemption", "genres": ["Drama"]},
            }
        ],
    }
    output_path = tmp_path / "movies_raw.json"
    output_path.write_text(json.dumps(payload), encoding="utf-8")
    return output_path, payload


def test_fetch_and_cache_falls_back_to_existing_cache(cached_payload):
    output_path, payload = cached_payload

    with patch("app.api.fetch_movies", side_effect=RapidAPIError("API unavailable")):
        result = fetch_and_cache_movies(
            genres=["Drama"],
            pages_per_genre=1,
            rows=5,
            output_path=output_path,
            fallback_to_cache=True,
        )

    assert result["meta"]["used_cache_fallback"] is True
    assert result["movies"][0]["id"] == payload["movies"][0]["id"]
    assert load_cached_movies(output_path)["movies"][0]["id"] == "tt0111161"
