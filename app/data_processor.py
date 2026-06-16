from app.api import RAW_MOVIES_PATH, load_cached_movies

STANDARD_FIELDS = (
    "id",
    "title",
    "genre",
    "description",
    "rating",
    "cast",
    "keywords",
)


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
    source = _merge_sources(list_data, details)

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

    return {
        "id": movie_id,
        "title": title,
        "genre": genre,
        "description": description,
        "rating": rating,
        "cast": cast,
        "keywords": keywords,
    }


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


if __name__ == "__main__":
    try:
        movies = load_parsed_movies()
        print(f"Parsed {len(movies)} movies from {RAW_MOVIES_PATH}")
        if movies:
            sample = movies[0]
            print(f"Sample: {sample['id']} - {sample['title']}")
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
        movies = parse_raw_movies(sample_payload)
        print(f"No cache found. Parsed {len(movies)} movies from sample data.")
        print(movies[0])
