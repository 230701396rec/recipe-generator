import json
import os
from urllib import error, request as urlrequest

from dotenv import load_dotenv
from flask import Flask, jsonify, render_template, request


load_dotenv()

app = Flask(__name__)

MODEL_NAME = os.getenv("MISTRAL_MODEL", "mistral-small-latest")
MISTRAL_CHAT_URL = "https://api.mistral.ai/v1/chat/completions"


def build_prompt(user_text, image_file):
    prompt = (
        "Generate a detailed recipe with a title, short introduction, "
        "ingredients list, and step-by-step cooking instructions based on "
        "the provided ingredients or dish description.\n\n"
        f"User input:\n{user_text or 'No text provided.'}"
    )

    if image_file and image_file.filename:
        prompt += (
            "\n\nThe user also uploaded an image file named "
            f"'{image_file.filename}'. If the text is limited, mention that the "
            "recipe is based mainly on the text input because image analysis is "
            "not enabled in this deployment."
        )

    return prompt


def generate_recipe_from_mistral(prompt):
    api_key = os.getenv("MISTRAL_API_KEY")
    if not api_key:
        raise ValueError("MISTRAL_API_KEY environment variable is not set.")

    payload = {
        "model": MODEL_NAME,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.7,
        "max_tokens": 800,
    }

    req = urlrequest.Request(
        MISTRAL_CHAT_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
        method="POST",
    )

    try:
        with urlrequest.urlopen(req, timeout=60) as response:
            response_data = json.loads(response.read().decode("utf-8"))
    except error.HTTPError as exc:
        details = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Mistral API returned HTTP {exc.code}: {details}") from exc
    except error.URLError as exc:
        raise RuntimeError(f"Unable to reach the Mistral API: {exc.reason}") from exc

    try:
        return response_data["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as exc:
        raise RuntimeError(f"Unexpected Mistral API response: {response_data}") from exc


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/generate", methods=["POST"])
def generate():
    user_text = request.form.get("ingredients", "").strip()
    image_file = request.files.get("image")

    if not user_text and (not image_file or not image_file.filename):
        return jsonify({"error": "Please enter ingredients or upload an image."}), 400

    try:
        prompt = build_prompt(user_text, image_file)
        recipe_text = generate_recipe_from_mistral(prompt)
        return jsonify({"recipe": recipe_text})
    except Exception as exc:
        return jsonify({"error": f"Recipe generation failed: {exc}"}), 500


@app.route("/health")
def health():
    return jsonify({"status": "ok"}), 200


if __name__ == "__main__":
    import os
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8000)))
