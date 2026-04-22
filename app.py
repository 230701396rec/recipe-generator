import os

from dotenv import load_dotenv
from flask import Flask, jsonify, render_template, request

from middleware.auth_middleware import AzureB2CAuth
from routes.recipe_routes import create_recipe_blueprint
from services.blob_service import BlobService
from services.cosmos_service import CosmosService
from services.recipe_service import RecipeGenerationService


load_dotenv()


def create_app():
    app = Flask(__name__)

    auth_client = AzureB2CAuth(
        tenant_name=os.getenv("AZURE_B2C_TENANT_NAME", "").strip(),
        tenant_domain=os.getenv("AZURE_B2C_TENANT_DOMAIN", "").strip(),
        policy_name=os.getenv("AZURE_B2C_POLICY", "").strip(),
        client_id=os.getenv("AZURE_B2C_CLIENT_ID", "").strip(),
        audience=os.getenv("AZURE_B2C_AUDIENCE", "").strip(),
        required_scopes=os.getenv("AZURE_B2C_API_SCOPES", "").strip(),
    )

    cosmos_service = CosmosService(
        connection_string=os.getenv("COSMOS_CONNECTION_STRING", "").strip(),
        endpoint=os.getenv("AZURE_COSMOS_ENDPOINT", "").strip(),
        key=os.getenv("AZURE_COSMOS_KEY", "").strip(),
        database_name=os.getenv("AZURE_COSMOS_DATABASE", "RecipeDB").strip(),
        users_container=os.getenv("AZURE_COSMOS_USERS_CONTAINER", "users").strip(),
        recipes_container=os.getenv("AZURE_COSMOS_RECIPES_CONTAINER", "Recipes").strip(),
    )

    blob_service = BlobService(
        connection_string=os.getenv("AZURE_BLOB_CONNECTION_STRING", "").strip(),
        container_name=os.getenv("AZURE_BLOB_CONTAINER", "recipe-images").strip(),
        public_base_url=os.getenv("AZURE_BLOB_PUBLIC_BASE_URL", "").strip(),
    )

    recipe_service = RecipeGenerationService(
        api_key=os.getenv("MISTRAL_API_KEY", "").strip(),
        model_name=os.getenv("MISTRAL_MODEL", "mistral-small-latest").strip(),
    )

    app.register_blueprint(
        create_recipe_blueprint(
            auth_client=auth_client,
            cosmos_service=cosmos_service,
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

    @app.route("/auth/config")
    def auth_config():
        host_url = request.host_url.rstrip("/")
        login_scopes = ["openid", "profile", "offline_access"]
        api_scopes = auth_client.required_scopes or []

        return jsonify(
            {
                "enabled": auth_client.is_enabled,
                "clientId": auth_client.client_id,
                "authority": auth_client.authority,
                "knownAuthority": auth_client.known_authority,
                "redirectUri": os.getenv("AZURE_B2C_REDIRECT_URI", host_url).strip(),
                "postLogoutRedirectUri": os.getenv(
                    "AZURE_B2C_POST_LOGOUT_REDIRECT_URI", host_url
                ).strip(),
                "loginScopes": login_scopes,
                "apiScopes": api_scopes,
            }
        )

    @app.route("/health")
    def health():
        return jsonify({"status": "ok"}), 200

    return app


app = create_app()


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8000)))
