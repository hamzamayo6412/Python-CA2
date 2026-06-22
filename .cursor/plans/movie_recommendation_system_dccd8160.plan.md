---
name: Movie Recommendation System
overview: Build a Flask-based movie recommendation system that fetches movie data from RapidAPI and uses Cosine Similarity to recommend similar movies, delivered in small, discrete phases.
todos:
  - id: phase1
    content: "Phase 1: Project setup — directory structure, virtualenv, requirements.txt, .env, run.py"
    status: completed
  - id: phase2
    content: "Phase 2: RapidAPI integration — app/api.py, fetch and cache raw movie data to data/movies_raw.json"
    status: completed
  - id: phase3a
    content: "Phase 3A: Parse raw API data — load movies_raw.json, extract and normalize core fields into structured records"
    status: completed
  - id: phase3b
    content: "Phase 3B: Build feature tags — combine genre/description/cast/keywords into tags column, save data/movies_clean.csv"
    status: completed
  - id: phase4
    content: "Phase 4: Recommendation engine — app/recommender.py using TF-IDF + cosine_similarity, pickle the matrix"
    status: pending
  - id: phase5
    content: "Phase 5: Flask routes — app/routes.py with homepage, movie detail, and recommendations endpoints"
    status: pending
  - id: phase6
    content: "Phase 6: Frontend — Jinja2 templates with Bootstrap 5 for movie grid, detail page, and recommendation cards"
    status: pending
  - id: phase7
    content: "Phase 7: Testing & polish — error handling, data refresh route, README"
    status: pending
isProject: false
---

# Movie Recommendation System - Implementation Plan

## Architecture Overview

```mermaid
flowchart TD
    User -->|"HTTP Request"| FlaskApp
    FlaskApp -->|"Fetch movies"| RapidAPI
    FlaskApp -->|"Store/cache"| JSONStore["JSON / CSV Store"]
    JSONStore -->|"Load features"| CosineSimilarity["Cosine Similarity Engine"]
    CosineSimilarity -->|"Top-N results"| FlaskApp
    FlaskApp -->|"Render HTML"| User
```

---

## Phase 1 — Project Setup

Goal: Establish project structure, virtual environment, and dependencies.

- Create directory structure:
  - `app/` — Flask app package
  - `app/templates/` — Jinja2 HTML templates
  - `app/static/` — CSS/JS assets
  - `data/` — cached movie data files
- Files to create: `requirements.txt`, `run.py`, `app/__init__.py`, `.env`
- Key dependencies: `flask`, `requests`, `python-dotenv`, `scikit-learn`, `pandas`, `numpy`

---

## Phase 2 — RapidAPI Integration

Goal: Connect to RapidAPI and fetch movie data.

- Choose a RapidAPI movie endpoint (e.g. **Movie Database (IMDB Alternative)** or **OTT Details**)
- Create `app/api.py` — wrapper with functions like `fetch_movies(genre, page)` and `fetch_movie_details(movie_id)`
- Store the `RAPIDAPI_KEY` and `RAPIDAPI_HOST` in `.env`, loaded via `python-dotenv`
- Write raw responses to `data/movies_raw.json` for offline use during development

---

## Phase 3A — Parse & Normalize Raw Data

Goal: Turn the nested IMDB236 cache into a flat, consistent dataset.

- Create [`app/data_processor.py`](app/data_processor.py) with parsing helpers only (no CSV export yet)
- Load [`data/movies_raw.json`](data/movies_raw.json) via `load_cached_movies()` from [`app/api.py`](app/api.py)
- For each cached record (`id`, `list_data`, `details`), map IMDB236 fields into a standard schema:
  - `id`, `title`, `genre`, `description`, `rating`, `cast`, `keywords`
- Prefer `details` when present; fall back to `list_data` for missing fields
- Deduplicate by `id` and drop records missing `id` or `title`
- Expose `parse_raw_movies(raw_data) -> list[dict]` returning normalized records

```mermaid
flowchart LR
    RawJSON["movies_raw.json"] -->|"load_cached_movies"| Parser["parse_raw_movies"]
    Parser -->|"normalize fields"| Records["list of movie dicts"]
```

---

## Phase 3B — Feature Tags & CSV Export

Goal: Engineer the text features the cosine similarity engine will use.

- Extend [`app/data_processor.py`](app/data_processor.py) with feature-building functions
- Add `build_tags(movie)` — concatenate `genre`, `description`, `cast`, and `keywords` into one lowercase `tags` string
- Handle nulls/empty lists safely (skip blanks, join list fields with spaces)
- Add `process_movies(raw_path, output_path)` pipeline: parse → build tags → save CSV
- Save output to [`data/movies_clean.csv`](data/movies_clean.csv) via `pandas` with columns: `id`, `title`, `genre`, `description`, `rating`, `cast`, `keywords`, `tags`
- Expose `load_clean_movies(path)` for use in Phases 4–5
- Runnable via `python -m app.data_processor`

```mermaid
flowchart LR
    Records["parsed movie dicts"] -->|"build_tags"| TagsCol["tags column"]
    TagsCol -->|"pandas.to_csv"| CleanCSV["movies_clean.csv"]
```

---


## Phase 4 — Recommendation Engine

Goal: Build the Cosine Similarity model.

- Create `app/recommender.py`
- Use `sklearn.feature_extraction.text.TfidfVectorizer` on the `tags` column
- Compute `cosine_similarity` matrix from the TF-IDF vectors
- Expose a function `get_recommendations(movie_title, n=10)` that returns the top-N similar movies
- Serialize the similarity matrix with `pickle` so it does not recompute on every request

```mermaid
flowchart LR
    tags["tags column"] -->|"TfidfVectorizer"| TFIDFMatrix["TF-IDF Matrix"]
    TFIDFMatrix -->|"cosine_similarity"| SimMatrix["Similarity Matrix (n x n)"]
    SimMatrix -->|"sort & slice"| TopN["Top-N Recommendations"]
```

---

## Phase 5 — Flask Routes & Backend Logic

Goal: Wire the recommendation engine into Flask routes.

- Create `app/routes.py` with:
  - `GET /` — homepage, lists movies (with search/filter)
  - `GET /movie/<id>` — movie detail page
  - `GET /recommend/<movie_title>` — returns recommendations (JSON or rendered page)
- Load the clean CSV and similarity matrix at app startup (cached in memory)

---

## Phase 6 — Frontend (Templates & UI)

Goal: Build a clean, functional UI with Jinja2 templates.

- `templates/base.html` — shared layout with navbar
- `templates/index.html` — movie grid with search bar
- `templates/movie_detail.html` — movie info + recommended movies carousel
- Use Bootstrap 5 via CDN for styling; no build step required

---

## Phase 7 — Testing & Polish

Goal: Verify end-to-end functionality and harden the app.

- Add error handling for failed API calls (fallback to cached data)
- Add a data refresh route `GET /refresh-data` (admin only via secret key)
- Manual testing of recommendations for accuracy
- Add `README.md` with setup instructions and API key configuration steps
