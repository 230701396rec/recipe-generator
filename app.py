import os
from flask import Flask, jsonify, render_template, request
from dotenv import load_dotenv
from mistralai.client import Mistral


# Load environment variables
load_dotenv()

app = Flask(__name__)

# Retrieve API key and model
API_KEY = os.getenv("MISTRAL_API_KEY")
MODEL_NAME = os.getenv("MISTRAL_MODEL", "mistral-small-latest")

if not API_KEY:
    raise ValueError("MISTRAL_API_KEY is not set.")

# Initialize Mistral client
client = Mistral(api_key=API_KEY)

def build_prompt(user_text):
    base_prompt = (
        "Generate a detailed recipe with a title, short introduction, "
        "ingredients list, and step-by-step cooking instructions based on "
        "the provided ingredients."
    )
    return f"{base_prompt}\n\nIngredients:\n{user_text}"

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/generate", methods=["POST"])
def generate():
    user_text = request.form.get("ingredients", "").strip()

    if not user_text:
        return jsonify({"error": "Please enter ingredients."}), 400

    try:
        response = client.chat.complete(
            model=MODEL_NAME,
            messages=[
                {
                    "role": "user",
                    "content": build_prompt(user_text)
                }
            ],
            temperature=0.7,
            max_tokens=800
        )

        recipe_text = response.choices[0].message.content
        return jsonify({"recipe": recipe_text})

    except Exception as exc:
        return jsonify({"error": f"Recipe generation failed: {exc}"}), 500

@app.route("/health")
def health():
    return jsonify({"status": "ok"}), 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8000)))
