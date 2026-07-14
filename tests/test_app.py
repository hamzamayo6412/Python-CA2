import pandas as pd
import pytest

from app import create_app
from app.data_processor import build_tags, parse_raw_movies
from app.recommender import MovieRecommender


@pytest.fixture
def app():
    application = create_app()
    application.config.update(
        {
            "TESTING": True,
            "REFRESH_SECRET_KEY": "test-refresh-key",
        }
    )
    return application


@pytest.fixture
def client(app):
    return app.test_client()


def test_index_returns_html(client):
    response = client.get("/")
    assert response.status_code == 200
    assert b"Browse Movies" in response.data


def test_index_json_format(client):
    response = client.get("/?format=json")
    assert response.status_code == 200
    data = response.get_json()
    assert "movies" in data
    assert data["count"] >= 1


def test_movie_detail_not_found(client):
    response = client.get("/movie/does-not-exist")
    assert response.status_code == 404


def test_refresh_data_requires_key(client):
    response = client.get("/refresh-data")
    assert response.status_code == 403


def test_build_tags():
    movie = {
        "genre": "Drama",
        "description": "A prison story.",
        "cast": "Actor One",
        "keywords": "hope",
    }
    assert build_tags(movie) == "drama a prison story. actor one hope"


def test_parse_flat_imdb236_record():
    """IMDB236 playground responses are flat title objects, not wrapped caches."""
    payload = [
        {
            "id": "tt21103218",
            "primaryTitle": "The Lost Bus",
            "type": "movie",
            "description": "A wayward school bus driver and a dedicated school teacher battle to save 22 children from a terrifying inferno.",
            "genres": ["Biography", "Drama", "History"],
            "interests": ["Disaster", "Biography", "Drama", "History", "Thriller"],
            "averageRating": 6.8,
        }
    ]
    movies = parse_raw_movies(payload)
    assert len(movies) == 1
    movie = movies[0]
    assert movie["id"] == "tt21103218"
    assert movie["title"] == "The Lost Bus"
    assert movie["genre"] == "Biography, Drama, History"
    assert movie["keywords"] == "Disaster, Biography, Drama, History, Thriller"
    assert movie["rating"] == 6.8
    assert movie["cast"] == ""
    assert movie["type"] == "movie"
    assert "disaster" in build_tags(movie)


def test_parse_raw_movies_deduplicates():
    payload = {
        "movies": [
            {
                "id": "tt1",
                "details": {"primaryTitle": "Movie A", "genres": ["Action"]},
            },
            {
                "id": "tt1",
                "details": {"primaryTitle": "Movie A Duplicate", "genres": ["Action"]},
            },
        ]
    }
    movies = parse_raw_movies(payload)
    assert len(movies) == 1
    assert movies[0]["title"] == "Movie A"


def test_recommender_prefers_similar_movies():
    sample = pd.DataFrame(
        [
            {
                "id": "tt1",
                "title": "Prison Drama",
                "genre": "Drama",
                "description": "prison escape",
                "rating": 8.0,
                "cast": "A",
                "keywords": "prison",
                "tags": "drama prison escape a prison",
            },
            {
                "id": "tt2",
                "title": "Space Adventure",
                "genre": "Sci-Fi",
                "description": "space travel",
                "rating": 7.5,
                "cast": "B",
                "keywords": "space",
                "tags": "sci-fi space travel b space",
            },
            {
                "id": "tt3",
                "title": "Jail Break",
                "genre": "Drama",
                "description": "men in prison",
                "rating": 8.2,
                "cast": "C",
                "keywords": "prison friendship",
                "tags": "drama men in prison c prison friendship",
            },
        ]
    )
    recommender = MovieRecommender().fit(sample)
    recommendations = recommender.get_recommendations("Prison Drama", n=1)
    assert recommendations[0]["title"] == "Jail Break"
