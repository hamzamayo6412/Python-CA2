import pickle
from pathlib import Path

import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from app.data_processor import CLEAN_MOVIES_PATH, load_clean_movies

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
RECOMMENDER_PATH = DATA_DIR / "recommender.pkl"


class MovieRecommender:
    def __init__(self, movies_df=None, similarity_matrix=None):
        self.movies_df = movies_df
        self.similarity_matrix = similarity_matrix

    def fit(self, movies_df):
        movies_df = movies_df.copy().reset_index(drop=True)
        tags = movies_df["tags"].fillna("").astype(str)

        vectorizer = TfidfVectorizer(stop_words="english")
        tfidf_matrix = vectorizer.fit_transform(tags)
        self.similarity_matrix = cosine_similarity(tfidf_matrix)
        self.movies_df = movies_df
        return self

    def _find_movie_index(self, movie_title):
        title = str(movie_title).strip().lower()
        if not title:
            raise ValueError("movie_title is required")

        exact_matches = self.movies_df[
            self.movies_df["title"].str.lower() == title
        ]
        if not exact_matches.empty:
            return exact_matches.index[0]

        partial_matches = self.movies_df[
            self.movies_df["title"].str.lower().str.contains(title, na=False)
        ]
        if partial_matches.empty:
            raise ValueError(f"Movie not found: {movie_title}")

        return partial_matches.index[0]

    def get_recommendations(self, movie_title, n=10):
        if self.movies_df is None or self.similarity_matrix is None:
            raise RuntimeError("Recommender is not fitted. Call fit() or load_model() first.")

        movie_index = self._find_movie_index(movie_title)
        scores = list(enumerate(self.similarity_matrix[movie_index]))
        scores.sort(key=lambda item: item[1], reverse=True)

        recommendations = []
        for index, score in scores:
            if index == movie_index:
                continue

            movie = self.movies_df.iloc[index].to_dict()
            movie["similarity_score"] = round(float(score), 4)
            recommendations.append(movie)

            if len(recommendations) >= n:
                break

        return recommendations


def build_recommender(movies_path=CLEAN_MOVIES_PATH):
    movies_df = load_clean_movies(movies_path)
    return MovieRecommender().fit(movies_df)


def save_model(recommender, path=RECOMMENDER_PATH):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    payload = {
        "movies_df": recommender.movies_df,
        "similarity_matrix": recommender.similarity_matrix,
    }

    with path.open("wb") as file:
        pickle.dump(payload, file)

    return path


def load_model(path=RECOMMENDER_PATH):
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Recommender model not found: {path}")

    with path.open("rb") as file:
        payload = pickle.load(file)

    return MovieRecommender(
        movies_df=payload["movies_df"],
        similarity_matrix=payload["similarity_matrix"],
    )


def train_and_save(movies_path=CLEAN_MOVIES_PATH, model_path=RECOMMENDER_PATH):
    recommender = build_recommender(movies_path)
    save_model(recommender, model_path)
    return recommender


_recommender = None


def get_recommender(reload=False, model_path=RECOMMENDER_PATH):
    global _recommender

    if _recommender is None or reload:
        _recommender = load_model(model_path)

    return _recommender


def get_recommendations(movie_title, n=10, model_path=RECOMMENDER_PATH):
    recommender = get_recommender(model_path=model_path)
    return recommender.get_recommendations(movie_title, n=n)


if __name__ == "__main__":
    recommender = train_and_save()
    print(f"Saved recommender model to {RECOMMENDER_PATH}")

    sample_title = recommender.movies_df.iloc[0]["title"]
    recommendations = recommender.get_recommendations(sample_title, n=5)
    print(f"Recommendations for '{sample_title}':")

    if recommendations:
        for movie in recommendations:
            print(f"- {movie['title']} (score: {movie['similarity_score']})")
    else:
        print("No similar movies found (dataset may contain only one movie).")
