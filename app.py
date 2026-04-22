import os

from dotenv import load_dotenv
from flask import Flask, jsonify, render_template, request

from routes.recipe_routes import create_recipe_blueprint
from services.blob_service import BlobService
from services.recipe_service import RecipeGenerationService


load_dotenv()


def create_app():
    app = Flask(__name__)

    blob_service = BlobService(
        connection_string=os.getenv("AZURE_STORAGE_CONNECTION_STRING", "").strip(),
        container_name=os.getenv("AZURE_BLOB_CONTAINER", "recipe-images").strip(),
        public_base_url=os.getenv("AZURE_BLOB_PUBLIC_BASE_URL", "").strip(),
        recipes_container_name=os.getenv("AZURE_RECIPES_CONTAINER", "recipes").strip(),
    )

    recipe_service = RecipeGenerationService(
        api_key=os.getenv("MISTRAL_API_KEY", "").strip(),
        model_name=os.getenv("MISTRAL_MODEL", "mistral-small-latest").strip(),
    )

    app.register_blueprint(
        create_recipe_blueprint(
            blob_service=blob_service,
            recipe_service=recipe_service,
        )
    )

    @app.route("/")
    def index():
        return render_template("index.html")

    @app.route("/dashboard")
    def dashboard():
        return render_template("dashboard.html")

    @app.route("/health")
    def health():
        return jsonify({"status": "ok"}), 200

    return app


app = create_app()


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8000)))
