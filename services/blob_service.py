import json
import mimetypes
import os
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from azure.core.exceptions import ResourceExistsError
from azure.storage.blob import BlobServiceClient, ContentSettings


class BlobService:
    def __init__(
        self,
        connection_string="",
        container_name="recipe-images",
        public_base_url="",
        recipes_container_name="recipes",
    ):
        self.connection_string = connection_string or os.getenv(
            "AZURE_STORAGE_CONNECTION_STRING",
            os.getenv("AZURE_BLOB_CONNECTION_STRING", ""),
        ).strip()
        self.container_name = container_name
        self.public_base_url = public_base_url.rstrip("/")
        self.recipes_container_name = recipes_container_name
        self.is_enabled = bool(self.connection_string)
        self._client = None

    def ensure_configured(self):
        if not self.is_enabled:
            raise RuntimeError(
                "Azure Blob Storage is not configured. Set "
                "AZURE_STORAGE_CONNECTION_STRING."
            )

    def _get_client(self):
        self.ensure_configured()
        if self._client is None:
            self._client = BlobServiceClient.from_connection_string(
                self.connection_string
            )
        return self._client

    def _get_container_client(self, container_name):
        container_client = self._get_client().get_container_client(container_name)
        try:
            container_client.create_container()
        except ResourceExistsError:
            pass
        return container_client

    @staticmethod
    def _utc_now():
        return datetime.now(timezone.utc).isoformat()

    @staticmethod
    def _normalize_ingredients(ingredients):
        if isinstance(ingredients, list):
            return ingredients
        if isinstance(ingredients, str):
            return [item.strip() for item in ingredients.split(",") if item.strip()]
        return []

    def upload_image(self, image_file, user_id=""):
        if not image_file or not image_file.filename:
            return None

        container_client = self._get_container_client(self.container_name)
        extension = Path(image_file.filename).suffix or ".bin"
        blob_name = f"{user_id or 'anonymous'}/{uuid4()}{extension}"
        content_type = image_file.mimetype or mimetypes.guess_type(
            image_file.filename
        )[0] or "application/octet-stream"

        image_file.stream.seek(0)
        container_client.upload_blob(
            name=blob_name,
            data=image_file.stream.read(),
            overwrite=True,
            content_settings=ContentSettings(content_type=content_type),
        )

        if self.public_base_url:
            return f"{self.public_base_url}/{blob_name}"

        return container_client.get_blob_client(blob_name).url

    def save_recipe(self, data, user=None):
        if not data.get("generatedRecipe"):
            raise RuntimeError("generatedRecipe is required.")

        container_client = self._get_container_client(self.recipes_container_name)
        blob_name = f"{uuid4()}.json"

        recipe = {
            "ingredients": self._normalize_ingredients(data.get("ingredients")),
            "generatedRecipe": data.get("generatedRecipe"),
            "createdAt": self._utc_now(),
        }

        if data.get("imageUrl"):
            recipe["imageUrl"] = data.get("imageUrl")
        if user and user.get("userId"):
            recipe["userId"] = user.get("userId")
        if user and user.get("email"):
            recipe["email"] = user.get("email")

        container_client.upload_blob(
            name=blob_name,
            data=json.dumps(recipe),
            overwrite=True,
            content_settings=ContentSettings(content_type="application/json"),
        )

        return {
            "message": "Recipe saved successfully",
            "blobName": blob_name,
            "recipe": recipe,
        }
