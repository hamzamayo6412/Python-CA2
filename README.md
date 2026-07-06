# Movie Recommendation System

A Flask web app that fetches movie data from RapidAPI (IMDB236), builds a content-based recommendation engine using **TF-IDF + Cosine Similarity**, and serves movie recommendations through a Bootstrap UI.

## Features

- Fetch and cache movies from RapidAPI
- Parse and clean movie metadata into a CSV dataset
- Recommend similar movies using cosine similarity on combined text features
- Browse, search, and filter movies in the browser
- JSON API endpoints for programmatic access
- Admin refresh endpoint with cache fallback when the API is unavailable

## Project Structure

```
app/
  __init__.py          # Flask app factory
  api.py               # RapidAPI client
  data_processor.py    # Parse raw JSON and export CSV
  data_refresh.py      # End-to-end refresh pipeline
  recommender.py       # TF-IDF + cosine similarity engine
  routes.py            # Web and API routes
  templates/           # Jinja2 HTML templates
  static/              # CSS assets
data/
  movies_raw.json      # Cached API responses
  movies_clean.csv     # Cleaned dataset
  recommender.pkl      # Pickled similarity model
run.py                 # App entry point
requirements.txt
.env
```

## Setup

### 1. Clone and create a virtual environment

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 2. Configure environment variables

Copy `.env.example` to `.env` and fill in your values:

```bash
cp .env.example .env
```

```env
SECRET_KEY=your-flask-secret-key
REFRESH_SECRET_KEY=your-admin-refresh-key
RAPIDAPI_KEY=your_rapidapi_key_here
RAPIDAPI_HOST=imdb236.p.rapidapi.com
```

**RapidAPI setup**

1. Create a free account at [RapidAPI](https://rapidapi.com/)
2. Subscribe to [IMDB236](https://rapidapi.com/octopusteam-octopusteam-default/api/imdb236)
3. Copy your API key into `RAPIDAPI_KEY` in `.env`

### 3. Fetch and prepare data

```bash
python -m app.api              # Fetch movies from RapidAPI -> data/movies_raw.json
python -m app.data_processor   # Parse and export -> data/movies_clean.csv
python -m app.recommender      # Train model -> data/recommender.pkl
```

Or refresh everything in one step via the admin endpoint after starting the app (see below).

### 4. Run the app

```bash
python run.py
```

Open [http://127.0.0.1:5000/](http://127.0.0.1:5000/)

## API Endpoints

| Endpoint | Description |
|---|---|
| `GET /` | Browse movies (HTML). Use `?format=json` for JSON |
| `GET /?q=term&genre=Drama` | Search and filter movies |
| `GET /movie/<imdb_id>` | Movie detail page with recommendations |
| `GET /recommend/<movie_title>?n=10` | JSON recommendations |
| `GET /refresh-data?key=<secret>` | Admin: refresh data from API |

## Admin Data Refresh

Refresh cached data, reprocess CSV, and retrain the model:

```bash
curl "http://127.0.0.1:5000/refresh-data?key=your-admin-refresh-key"
```

If the RapidAPI request fails but cached data exists, the app falls back to the existing `movies_raw.json` and returns HTTP `207` with `"used_cache_fallback": true`.

## How Recommendations Work

1. Text fields (`genre`, `description`, `cast`, `keywords`) are combined into a `tags` column
2. `TfidfVectorizer` converts tags into numerical vectors
3. `cosine_similarity` computes how similar each movie pair is
4. For a selected movie, the top-N highest-scoring matches are returned

## Manual Testing Checklist

1. **Browse** — Open `/` and confirm movies appear in the grid
2. **Search** — Search for a known title (e.g. `shawshank`) and verify results
3. **Genre filter** — Filter by genre and confirm matching movies show
4. **Detail page** — Open a movie and verify cast, description, and keywords
5. **Recommendations** — With 2+ movies in the dataset, confirm similar titles appear on the detail page
6. **JSON API** — `curl "http://127.0.0.1:5000/?format=json"`
7. **Refresh fallback** — Call `/refresh-data` with a valid key; if the API fails, confirm cached data is still used

## Run Tests

```bash
pip install pytest
pytest tests/ -v
```

## Troubleshooting

| Issue | Fix |
|---|---|
| `RAPIDAPI_KEY is missing` | Add your key to `.env` |
| `Missing data files` | Run `python -m app.data_processor` |
| No recommendations shown | Fetch more movies (need 2+ titles), then reprocess and retrain |
| `403` on refresh | Pass the correct `REFRESH_SECRET_KEY` as `?key=` |
