import os
from flask import Flask, jsonify, render_template, request
from dotenv import load_dotenv
from mistralai import Mistral

# Load environment variables (for local development)
load_dotenv()

app = Flask(__name__)

MODEL_NAME = os.getenv("MISTRAL_MODEL", "mistral-small-latest")


def build_prompt(user_text):
    return (
        "Generate a detailed recipe with a title, short introduction, "
        "ingredients list, and step-by-step cooking instructions based on "
        f"the provided ingredients:\n{user_text}"
    )


def get_mistral_client():
    api_key = os.getenv("MISTRAL_API_KEY")
    if not api_key:
        raise ValueError("MISTRAL_API_KEY environment variable is not set.")
    return Mistral(api_key=api_key)


@app.route("/")
def index():
    # Temporary fallback to ensure deployment works
    return "Recipe Generator is running successfully!"


@app.route("/generate", methods=["POST"])
def generate():
    user_text = request.form.get("ingredients", "").strip()

    if not user_text:
        return jsonify({"error": "Please enter ingredients."}), 400

    try:
        client = get_mistral_client()
        response = client.chat.complete(
            model=MODEL_NAME,
            messages=[{"role": "user", "content": build_prompt(user_text)}],
        )
        recipe_text = response.choices[0].message.content
        return jsonify({"recipe": recipe_text})
    except Exception as exc:
        return jsonify({"error": f"Recipe generation failed: {str(exc)}"}), 500


@app.route("/health")
def health():
    return jsonify({"status": "ok"}), 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8000)))