from flask import Blueprint, abort, current_app, jsonify, redirect, render_template, request, url_for

bp = Blueprint("main", __name__)


def _serialize_movie(movie):
    record = dict(movie)
    rating = record.get("rating")
    if rating is None or (isinstance(rating, float) and rating != rating):
        record["rating"] = None
    else:
        record["rating"] = float(rating)

    for field in ("id", "title", "genre", "description", "cast", "keywords", "tags"):
        value = record.get(field)
        record[field] = "" if value is None else str(value)

    if "similarity_score" in record:
        record["similarity_score"] = float(record["similarity_score"])

    return record


def _get_movies():
    return current_app.config["MOVIES_DF"]


def _get_recommender():
    return current_app.config["RECOMMENDER"]


def _wants_json():
    if request.args.get("format") == "json":
        return True
    return request.accept_mimetypes.best_match(["application/json", "text/html"]) == "application/json"


def _get_genres(movies_df):
    genres = set()
    for value in movies_df["genre"].fillna(""):
        for part in str(value).split(","):
            genre = part.strip()
            if genre:
                genres.add(genre)
    return sorted(genres)


def _filter_movies(movies_df, query=None, genre=None):
    filtered = movies_df.copy()

    if genre:
        genre_value = genre.strip().lower()
        filtered = filtered[
            filtered["genre"].fillna("").str.lower().str.contains(genre_value, na=False)
        ]

    if query:
        query_value = query.strip().lower()
        search_columns = ["title", "genre", "description", "cast", "keywords"]
        mask = False
        for column in search_columns:
            mask = mask | filtered[column].fillna("").str.lower().str.contains(
                query_value, na=False
            )
        filtered = filtered[mask]

    return filtered


@bp.route("/")
def index():
    query = request.args.get("q", "").strip()
    genre = request.args.get("genre", "").strip()

    movies_df = _get_movies()
    filtered = _filter_movies(movies_df, query=query or None, genre=genre or None)
    movies = [_serialize_movie(row) for _, row in filtered.iterrows()]

    if _wants_json():
        return jsonify(
            {
                "count": len(movies),
                "query": query,
                "genre": genre,
                "movies": movies,
            }
        )

    return render_template(
        "index.html",
        movies=movies,
        count=len(movies),
        query=query,
        genre=genre,
        genres=_get_genres(movies_df),
    )


@bp.route("/movie/<movie_id>")
def movie_detail(movie_id):
    movies_df = _get_movies()
    matches = movies_df[movies_df["id"].astype(str) == str(movie_id)]

    if matches.empty:
        if _wants_json():
            return jsonify({"error": f"Movie not found: {movie_id}"}), 404
        abort(404)

    movie = _serialize_movie(matches.iloc[0])
    recommendations = []

    try:
        recommender = _get_recommender()
        recommendations = [
            _serialize_movie(item)
            for item in recommender.get_recommendations(movie["title"], n=10)
        ]
    except (ValueError, RuntimeError):
        recommendations = []

    if _wants_json():
        return jsonify({"movie": movie, "recommendations": recommendations})

    return render_template(
        "movie_detail.html",
        movie=movie,
        recommendations=recommendations,
    )


@bp.route("/recommend/<path:movie_title>")
def recommend(movie_title):
    n = request.args.get("n", default=10, type=int)
    n = max(1, min(n, 50))

    try:
        recommender = _get_recommender()
        recommendations = recommender.get_recommendations(movie_title, n=n)
    except ValueError as error:
        if _wants_json():
            return jsonify({"error": str(error)}), 404
        abort(404)
    except RuntimeError as error:
        if _wants_json():
            return jsonify({"error": str(error)}), 503
        abort(503)

    payload = {
        "movie_title": movie_title,
        "count": len(recommendations),
        "recommendations": [_serialize_movie(movie) for movie in recommendations],
    }

    if _wants_json():
        return jsonify(payload)

    movies_df = _get_movies()
    matches = movies_df[
        movies_df["title"].str.lower() == movie_title.strip().lower()
    ]
    if not matches.empty:
        return redirect(url_for("main.movie_detail", movie_id=matches.iloc[0]["id"]))

    abort(404)


@bp.route("/refresh-data")
def refresh_data():
    admin_key = current_app.config.get("REFRESH_SECRET_KEY", "")
    provided_key = request.args.get("key", "").strip()

    if not admin_key or provided_key != admin_key:
        if _wants_json():
            return jsonify({"error": "Unauthorized"}), 403
        abort(403)

    from app.api import RapidAPIError
    from app.data_refresh import refresh_all_data, reload_app_data

    try:
        result = refresh_all_data()
        reload_app_data(current_app)
    except RapidAPIError as error:
        return jsonify({"error": str(error), "used_cache_fallback": False}), 502
    except FileNotFoundError as error:
        return jsonify({"error": str(error)}), 404

    status_code = 200 if not result.get("used_cache_fallback") else 207
    return jsonify(
        {
            "message": "Data refreshed successfully",
            **result,
        }
    ), status_code
