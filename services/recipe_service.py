import json
from urllib import error, request as urlrequest


MISTRAL_CHAT_URL = "https://api.mistral.ai/v1/chat/completions"


class RecipeGenerationService:
    def __init__(self, api_key, model_name):
        self.api_key = api_key
        self.model_name = model_name

    @staticmethod
    def build_prompt(user_text, image_file):
        import base64

        text_prompt = (
            "You are an expert chef. Please generate a detailed recipe with a title, short introduction, "
            "ingredients list, and step-by-step cooking instructions.\n\n"
        )

        has_image = bool(image_file and image_file.filename)
        
        if has_image:
            text_prompt += (
                "Based on the provided image:\n"
                "1. If the image shows a completed dish, identify it and generate the recipe for it.\n"
                "2. If the image shows raw ingredients, generate a recipe that uses these ingredients.\n\n"
            )

        if user_text:
            text_prompt += f"Additionally, consider the following text input:\n{user_text}\n"

        if not has_image:
            return text_prompt

        image_bytes = image_file.read()
        image_file.seek(0)
        base64_image = base64.b64encode(image_bytes).decode("utf-8")
        
        mime_type = image_file.content_type if hasattr(image_file, 'content_type') and image_file.content_type else "image/jpeg"
        image_url = f"data:{mime_type};base64,{base64_image}"

        return [
            {
                "type": "text",
                "text": text_prompt
            },
            {
                "type": "image_url",
                "image_url": image_url
            }
        ]

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
