import logging
import os
from datetime import datetime, timezone
from uuid import uuid4

from azure.cosmos import CosmosClient, PartitionKey
from azure.cosmos.exceptions import CosmosHttpResponseError, CosmosResourceNotFoundError


logger = logging.getLogger(__name__)


class CosmosService:
    def __init__(
        self,
        connection_string="",
        database_name="RecipeDB",
        users_container="users",
        recipes_container="Recipes",
        endpoint="",
        key="",
    ):
        self.connection_string = connection_string or os.getenv(
            "COSMOS_CONNECTION_STRING", ""
        ).strip()
        self.endpoint = endpoint
        self.key = key
        self.database_name = database_name
        self.users_container_name = users_container
        self.recipes_container_name = recipes_container
        self.is_enabled = bool(
            self.connection_string
            or (
                self.endpoint
                and self.key
                and self.database_name
                and self.users_container_name
                and self.recipes_container_name
            )
        )
        self._database = None
        self._users = None
        self._recipes = None

    def ensure_configured(self):
        if not self.is_enabled:
            raise RuntimeError(
                "Azure Cosmos DB is not configured. Set COSMOS_CONNECTION_STRING "
                "or the AZURE_COSMOS_* environment variables."
            )

    def _build_client(self):
        if self.connection_string:
            return CosmosClient.from_connection_string(self.connection_string)
        return CosmosClient(self.endpoint, credential=self.key)

    def _initialize(self):
        self.ensure_configured()
        if self._database and self._users and self._recipes:
            return

        client = self._build_client()
        self._database = client.create_database_if_not_exists(id=self.database_name)
        self._users = self._database.create_container_if_not_exists(
            id=self.users_container_name,
            partition_key=PartitionKey(path="/id"),
        )
        self._recipes = self._database.create_container_if_not_exists(
            id=self.recipes_container_name,
            partition_key=PartitionKey(path="/userId"),
        )

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

    def add_recipe(self, data, user):
        self._initialize()

        try:
            if not user or not user.get("userId"):
                raise RuntimeError("Authenticated user is required.")
            if not data.get("generatedRecipe"):
                raise RuntimeError("generatedRecipe is required.")

            document = {
                "id": str(uuid4()),
                "userId": user["userId"],
                "email": user.get("email", ""),
                "ingredients": self._normalize_ingredients(data.get("ingredients", [])),
                "generatedRecipe": data["generatedRecipe"],
                "createdAt": self._utc_now(),
            }

            if data.get("imageUrl"):
                document["imageUrl"] = data["imageUrl"]
            if "favorite" in data:
                document["favorite"] = bool(data.get("favorite"))

            created = self._recipes.create_item(document)
            return created
        except KeyError as exc:
            logger.error("Missing required recipe field: %s", exc)
            raise RuntimeError(f"Missing required recipe field: {exc}") from exc
        except CosmosHttpResponseError as exc:
            logger.exception("Cosmos DB failed to add recipe for user %s", user.get("userId"))
            raise RuntimeError("Failed to save recipe to Cosmos DB.") from exc

    def get_recipes_by_user(self, user_id, page=1, page_size=20):
        self._initialize()
        page = max(int(page or 1), 1)
        page_size = max(min(int(page_size or 20), 100), 1)

        try:
            if not user_id:
                raise RuntimeError("userId is required.")
            query = (
                "SELECT * FROM c WHERE c.userId = @userId "
                "ORDER BY c.createdAt DESC"
            )
            parameters = [{"name": "@userId", "value": user_id}]
            items = list(
                self._recipes.query_items(
                    query=query,
                    parameters=parameters,
                    partition_key=user_id,
                )
            )
            start = (page - 1) * page_size
            end = start + page_size
            return {
                "recipes": items[start:end],
                "page": page,
                "pageSize": page_size,
                "total": len(items),
            }
        except CosmosHttpResponseError as exc:
            logger.exception("Cosmos DB failed to query recipes for user %s", user_id)
            raise RuntimeError("Failed to load recipes from Cosmos DB.") from exc

    def get_recipe_by_id(self, recipe_id, user_id):
        self._initialize()

        try:
            return self._recipes.read_item(item=recipe_id, partition_key=user_id)
        except CosmosResourceNotFoundError:
            logger.warning("Recipe %s not found for user %s", recipe_id, user_id)
            return None
        except CosmosHttpResponseError as exc:
            logger.exception("Cosmos DB failed to read recipe %s for user %s", recipe_id, user_id)
            raise RuntimeError("Failed to load recipe from Cosmos DB.") from exc

    def delete_recipe(self, recipe_id, user_id):
        self._initialize()

        try:
            if not recipe_id or not user_id:
                raise RuntimeError("recipe_id and user_id are required.")
            recipe = self.get_recipe_by_id(recipe_id, user_id)
            if not recipe:
                return False
            if recipe.get("userId") != user_id:
                logger.warning(
                    "User %s attempted to delete recipe %s owned by %s",
                    user_id,
                    recipe_id,
                    recipe.get("userId"),
                )
                return False
            self._recipes.delete_item(item=recipe_id, partition_key=user_id)
            return True
        except CosmosHttpResponseError as exc:
            logger.exception("Cosmos DB failed to delete recipe %s for user %s", recipe_id, user_id)
            raise RuntimeError("Failed to delete recipe from Cosmos DB.") from exc

    def set_recipe_favorite(self, recipe_id, user_id, favorite):
        self._initialize()

        try:
            recipe = self.get_recipe_by_id(recipe_id, user_id)
            if not recipe:
                raise RuntimeError("Recipe not found.")
            recipe["favorite"] = bool(favorite)
            self._recipes.replace_item(item=recipe_id, body=recipe)
            return recipe
        except CosmosHttpResponseError as exc:
            logger.exception(
                "Cosmos DB failed to update favorite for recipe %s and user %s",
                recipe_id,
                user_id,
            )
            raise RuntimeError("Failed to update favorite recipe.") from exc

    def list_all_recipes(self):
        self._initialize()

        try:
            items = self._recipes.query_items(
                query="SELECT * FROM c ORDER BY c.createdAt DESC",
                enable_cross_partition_query=True,
            )
            return list(items)
        except CosmosHttpResponseError as exc:
            logger.exception("Cosmos DB failed to load all recipes")
            raise RuntimeError("Failed to load admin recipes from Cosmos DB.") from exc
