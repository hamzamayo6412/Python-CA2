import os

from dotenv import load_dotenv
from flask import Flask, render_template

from app.data_processor import CLEAN_MOVIES_PATH, load_clean_movies
from app.recommender import RECOMMENDER_PATH, get_recommender, train_and_save

load_dotenv()


def _load_app_data():
    if not RECOMMENDER_PATH.exists():
        if not CLEAN_MOVIES_PATH.exists():
            raise FileNotFoundError(
                "Missing data files. Run `python -m app.data_processor` first."
            )
        train_and_save()

    movies_df = load_clean_movies()
    recommender = get_recommender(reload=True)
    return movies_df, recommender


def create_app():
    app = Flask(__name__)
    app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "dev-secret-key")
    app.config["REFRESH_SECRET_KEY"] = os.getenv("REFRESH_SECRET_KEY", app.config["SECRET_KEY"])

    movies_df, recommender = _load_app_data()
    app.config["MOVIES_DF"] = movies_df
    app.config["RECOMMENDER"] = recommender

    from app.routes import bp

    app.register_blueprint(bp)

    @app.errorhandler(403)
    def forbidden(error):
        from flask import request

        if request.accept_mimetypes.best_match(["application/json", "text/html"]) == "application/json":
            return {"error": "Forbidden"}, 403
        return render_template("404.html"), 403

    @app.errorhandler(404)
    def not_found(error):
        from flask import request

        if request.accept_mimetypes.best_match(["application/json", "text/html"]) == "application/json":
            return {"error": "Not found"}, 404
        return render_template("404.html"), 404

    return app
