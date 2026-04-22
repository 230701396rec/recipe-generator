import json
from urllib import error, request as urlrequest


MISTRAL_CHAT_URL = "https://api.mistral.ai/v1/chat/completions"


class RecipeGenerationService:
    def __init__(self, api_key, model_name):
        self.api_key = api_key
        self.model_name = model_name

    @staticmethod
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

    def generate_recipe(self, prompt):
        if not self.api_key:
            raise ValueError("MISTRAL_API_KEY environment variable is not set.")

        payload = {
            "model": self.model_name,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.7,
            "max_tokens": 800,
        }

        req = urlrequest.Request(
            MISTRAL_CHAT_URL,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self.api_key}",
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
            raise RuntimeError(
                f"Mistral API returned HTTP {exc.code}: {details}"
            ) from exc
        except error.URLError as exc:
            raise RuntimeError(f"Unable to reach the Mistral API: {exc.reason}") from exc

        try:
            return response_data["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise RuntimeError(f"Unexpected Mistral API response: {response_data}") from exc
