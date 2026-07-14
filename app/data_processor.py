from pathlib import Path

import pandas as pd

from app.api import RAW_MOVIES_PATH, load_cached_movies

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
CLEAN_MOVIES_PATH = DATA_DIR / "movies_clean.csv"

STANDARD_FIELDS = (
    "id",
    "title",
    "genre",
    "description",
    "rating",
    "cast",
    "keywords",
)

CSV_COLUMNS = STANDARD_FIELDS + ("tags",)


def _as_text(value):
    if value is None:
        return ""
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, (int, float)):
        return str(value)
    return ""


def _join_values(values):
    parts = []
    for value in values:
        text = _as_text(value)
        if text:
            parts.append(text)
    return ", ".join(parts)


def _extract_list_field(data, *keys):
    for key in keys:
        value = data.get(key)
        if value is None:
            continue

        if isinstance(value, list):
            items = []
            for item in value:
                if isinstance(item, dict):
                    text = (
                        item.get("name")
                        or item.get("text")
                        or item.get("keyword")
                        or item.get("primaryName")
                        or item.get("fullName")
                    )
                    text = _as_text(text)
                    if text:
                        items.append(text)
                else:
                    text = _as_text(item)
                    if text:
                        items.append(text)
            if items:
                return ", ".join(items)

        text = _as_text(value)
        if text:
            return text

    return ""


def _pick_first(data, *keys):
    for key in keys:
        value = data.get(key)
        if value is None:
            continue
        if isinstance(value, str) and not value.strip():
            continue
        return value
    return None


def _normalize_rating(value):
    if value is None or value == "":
        return None

    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _merge_sources(*sources):
    merged = {}
    for source in sources:
        if isinstance(source, dict):
            merged.update(source)
    return merged


def _parse_single_record(record):
    if not isinstance(record, dict):
        return None

    details = record.get("details") if isinstance(record.get("details"), dict) else {}
    list_data = record.get("list_data") if isinstance(record.get("list_data"), dict) else {}
    wrapper_keys = {"details", "list_data", "genre_query"}
    flat_source = {
        key: value
        for key, value in record.items()
        if key not in wrapper_keys and not isinstance(value, dict)
    }
    source = _merge_sources(flat_source, list_data, details)

    movie_id = _as_text(
        record.get("id")
        or source.get("id")
        or source.get("imdbId")
        or source.get("imdb_id")
    )
    title = _as_text(
        _pick_first(source, "primaryTitle", "originalTitle", "title", "name")
    )

    if not movie_id or not title:
        return None

    genre = _extract_list_field(source, "genres", "genre")
    if not genre and record.get("genre_query"):
        genre = _as_text(record.get("genre_query"))

    description = _as_text(
        _pick_first(
            source,
            "plot",
            "plotSummary",
            "description",
            "overview",
            "plotText",
            "shortDescription",
        )
    )

    rating = _normalize_rating(
        _pick_first(
            source,
            "averageRating",
            "imdbRating",
            "rating",
            "aggregateRating",
            "voteAverage",
        )
    )

    cast = _extract_list_field(source, "stars", "cast", "actors", "topCast")
    keywords = _extract_list_field(source, "keywords", "keywordList", "interests")
    content_type = _as_text(_pick_first(source, "type", "titleType"))

    parsed = {
        "id": movie_id,
        "title": title,
        "genre": genre,
        "description": description,
        "rating": rating,
        "cast": cast,
        "keywords": keywords,
    }
    if content_type:
        parsed["type"] = content_type

    return parsed


def parse_raw_movies(raw_data):
    """Parse cached raw API data into normalized movie records."""
    if isinstance(raw_data, dict):
        records = raw_data.get("movies", [])
    elif isinstance(raw_data, list):
        records = raw_data
    else:
        records = []

    parsed_movies = []
    seen_ids = set()

    for record in records:
        movie = _parse_single_record(record)
        if not movie:
            continue

        if movie["id"] in seen_ids:
            continue

        seen_ids.add(movie["id"])
        parsed_movies.append(movie)

    return parsed_movies


def load_parsed_movies(path=RAW_MOVIES_PATH):
    """Load raw cached movies and return parsed records."""
    raw_data = load_cached_movies(path)
    return parse_raw_movies(raw_data)


def build_tags(movie):
    """Combine text fields into a single lowercase tags string for similarity."""
    parts = []
    for field in ("type", "genre", "description", "cast", "keywords"):
        text = _as_text(movie.get(field))
        if text:
            parts.append(text)

    return " ".join(parts).lower()


def _add_tags_to_movies(movies):
    enriched = []
    for movie in movies:
        record = dict(movie)
        record["tags"] = build_tags(record)
        enriched.append(record)
    return enriched


def process_movies(raw_path=RAW_MOVIES_PATH, output_path=CLEAN_MOVIES_PATH):
    """Parse raw API data, build tags, and save cleaned movies to CSV."""
    raw_data = load_cached_movies(raw_path)
    movies = parse_raw_movies(raw_data)
    movies_with_tags = _add_tags_to_movies(movies)

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    dataframe = pd.DataFrame(movies_with_tags, columns=CSV_COLUMNS)
    dataframe.to_csv(output_path, index=False)

    return dataframe


def load_clean_movies(path=CLEAN_MOVIES_PATH):
    """Load cleaned movie data from CSV."""
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Cleaned movie file not found: {path}")

    return pd.read_csv(path)


if __name__ == "__main__":
    try:
        dataframe = process_movies()
        print(f"Saved {len(dataframe)} movies to {CLEAN_MOVIES_PATH}")
        if not dataframe.empty:
            sample = dataframe.iloc[0]
            print(f"Sample: {sample['id']} - {sample['title']}")
            print(f"Tags: {sample['tags']}")
    except FileNotFoundError:
        sample_payload = {
            "movies": [
                {
                    "id": "tt0111161",
                    "genre_query": "Drama",
                    "list_data": {
                        "id": "tt0111161",
                        "primaryTitle": "The Shawshank Redemption",
                        "averageRating": 9.3,
                        "genres": ["Drama"],
                    },
                    "details": {
                        "id": "tt0111161",
                        "primaryTitle": "The Shawshank Redemption",
                        "plot": "Two imprisoned men bond over years.",
                        "averageRating": 9.3,
                        "genres": ["Drama"],
                        "stars": ["Tim Robbins", "Morgan Freeman"],
                        "keywords": ["prison", "friendship"],
                    },
                }
            ]
        }
        movies = _add_tags_to_movies(parse_raw_movies(sample_payload))
        dataframe = pd.DataFrame(movies, columns=CSV_COLUMNS)
        CLEAN_MOVIES_PATH.parent.mkdir(parents=True, exist_ok=True)
        dataframe.to_csv(CLEAN_MOVIES_PATH, index=False)
        print(f"No raw cache found. Saved {len(dataframe)} sample movies to {CLEAN_MOVIES_PATH}")
        print(dataframe.iloc[0]["tags"])
