import base64
import json
import logging

from flask import Blueprint, jsonify, request


logger = logging.getLogger(__name__)
def _payload_field(payload, key, default=""):
    value = payload.get(key, default)
    return value.strip() if isinstance(value, str) else value


def _get_request_payload():
    if request.is_json:
        return request.get_json(silent=True) or {}
    return request.form


def _get_pagination():
    page = request.args.get("page", default=1, type=int)
    page_size = request.args.get("page_size", default=20, type=int)
    return page, page_size


def get_current_user():
    principal = request.headers.get("X-MS-CLIENT-PRINCIPAL")
    if not principal:
        return None

    try:
        decoded = base64.b64decode(principal)
        user_data = json.loads(decoded)
    except (ValueError, json.JSONDecodeError) as exc:
        logger.warning("Invalid Easy Auth principal header: %s", exc)
        return None

    claims = user_data.get("claims", [])

    def find_claim(*names):
        normalized = {name.lower() for name in names}
        for claim in claims:
            claim_type = str(claim.get("typ", "")).lower()
            if claim_type in normalized:
                return claim.get("val")
        return None

    user_id = (
        user_data.get("userId")
        or find_claim(
            "http://schemas.microsoft.com/identity/claims/objectidentifier",
            "http://schemas.xmlsoap.org/ws/2005/05/identity/claims/nameidentifier",
            "nameidentifier",
            "sub",
        )
        or request.headers.get("X-MS-CLIENT-PRINCIPAL-ID")
    )
    email = (
        user_data.get("userDetails")
        or find_claim(
            "http://schemas.xmlsoap.org/ws/2005/05/identity/claims/emailaddress",
            "preferred_username",
            "emails",
        )
        or request.headers.get("X-MS-CLIENT-PRINCIPAL-NAME")
    )
    roles = [
        claim.get("val")
        for claim in claims
        if str(claim.get("typ", "")).lower()
        in {
            "roles",
            "http://schemas.microsoft.com/ws/2008/06/identity/claims/role",
        }
    ]

    if not user_id:
        return None

    return {
        "userId": user_id,
        "email": email or "",
        "roles": roles,
        "principal": user_data,
    }


def _require_user():
    try:
        user = get_current_user()
        if not user:
            return None, (jsonify({"error": "Unauthorized"}), 401)
        return user, None
    except Exception:
        logger.exception("Unexpected failure while resolving Easy Auth user")
        return None, (jsonify({"error": "Unauthorized"}), 401)


def create_recipe_blueprint(blob_service, recipe_service):
    recipe_bp = Blueprint("recipe", __name__)

    @recipe_bp.route("/generate", methods=["POST"])
    def generate_recipe_public():
        return _generate_recipe(recipe_service, None)

    @recipe_bp.route("/generate-recipe", methods=["POST"])
    def generate_recipe_protected():
        user, error_response = _require_user()
        if error_response:
            return error_response
        return _generate_recipe(recipe_service, user)

    @recipe_bp.route("/save-recipe", methods=["POST"])
    def save_recipe():
        user, error_response = _require_user()
        if error_response:
            return error_response

        payload = _get_request_payload()
        image_file = request.files.get("image")
        ingredients = _payload_field(payload, "ingredients")
        generated_recipe = _payload_field(payload, "generatedRecipe") or _payload_field(
            payload, "recipe"
        )
        if not generated_recipe:
            return jsonify({"error": "generatedRecipe is required."}), 400

        try:
            image_url = None
            if image_file and image_file.filename:
                image_url = blob_service.upload_image(image_file, user["userId"])

            recipe = blob_service.save_recipe(
                {
                    "ingredients": ingredients,
                    "generatedRecipe": generated_recipe,
                    "imageUrl": image_url,
                },
                user,
            )
            return jsonify(recipe), 201
        except Exception as exc:
            return jsonify({"error": f"Unable to save recipe: {exc}"}), 500

    @recipe_bp.route("/my-recipes", methods=["GET"])
    def my_recipes():
        user, error_response = _require_user()
        if error_response:
            return error_response

        try:
            page, page_size = _get_pagination()
            return (
                jsonify(
                    {
                        "recipes": [],
                        "page": page,
                        "pageSize": page_size,
                        "total": 0,
                        "user": {
                            "userId": user["userId"],
                            "email": user.get("email", ""),
                        },
                    }
                ),
                200,
            )
        except Exception as exc:
            return jsonify({"error": f"Unable to load recipes: {exc}"}), 500

    @recipe_bp.route("/recipe/<recipe_id>", methods=["GET"])
    def get_recipe(recipe_id):
        user, error_response = _require_user()
        if error_response:
            return error_response

        try:
            return (
                jsonify(
                    {
                        "error": "Recipe lookup is not available when using Blob-only storage."
                    }
                ),
                404,
            )
        except Exception as exc:
            return jsonify({"error": f"Unable to load recipe: {exc}"}), 500

    @recipe_bp.route("/recipe/<recipe_id>", methods=["DELETE"])
    def delete_recipe(recipe_id):
        user, error_response = _require_user()
        if error_response:
            return error_response

        try:
            return (
                jsonify(
                    {
                        "error": "Recipe deletion is not available when using Blob-only storage."
                    }
                ),
                404,
            )
        except Exception as exc:
            return jsonify({"error": f"Unable to delete recipe: {exc}"}), 500

    @recipe_bp.route("/favorite-recipes/<recipe_id>", methods=["POST"])
    def toggle_favorite(recipe_id):
        user, error_response = _require_user()
        if error_response:
            return error_response

        try:
            return (
                jsonify(
                    {
                        "error": "Favorite updates are not available when using Blob-only storage."
                    }
                ),
                404,
            )
        except Exception as exc:
            return jsonify({"error": f"Unable to update favorite: {exc}"}), 500

    @recipe_bp.route("/admin/recipes", methods=["GET"])
    def admin_recipes():
        user, error_response = _require_user()
        if error_response:
            return error_response
        if "admin" not in set(user.get("roles", [])):
            return jsonify({"error": "You do not have permission to access this route."}), 403

        try:
            return jsonify({"recipes": []}), 200
        except Exception as exc:
            return jsonify({"error": f"Unable to load admin recipes: {exc}"}), 500

    return recipe_bp


def _generate_recipe(recipe_service, user):
    payload = _get_request_payload()
    user_text = _payload_field(payload, "ingredients")
    image_file = request.files.get("image")

    if not user_text and (not image_file or not image_file.filename):
        return jsonify({"error": "Please enter ingredients or upload an image."}), 400

    try:
        prompt = recipe_service.build_prompt(user_text, image_file)
        recipe_text = recipe_service.generate_recipe(prompt)

        response = {"recipe": recipe_text}
        if user:
            response["user"] = {
                "email": user.get("email"),
                "userId": user.get("userId"),
            }
        return jsonify(response), 200
    except Exception as exc:
        return jsonify({"error": f"Recipe generation failed: {exc}"}), 500
