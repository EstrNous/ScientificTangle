import json
from typing import Any

import httpx

from .core.config import Settings


class YandexModelClient:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    @property
    def is_configured(self) -> bool:
        return self.settings.yandex_enabled

    def embedding(self, text: str, model_name: str, dimensions: int) -> list[float]:
        self.ensure_configured()
        payload = {
            "modelUri": self.model_uri("emb", model_name),
            "text": text,
            "dim": str(dimensions),
        }
        data = self.post_json(f"{self.settings.yandex_foundation_base_url}/textEmbedding", payload)
        return [float(value) for value in data.get("embedding", [])]

    def complete_text(self, system_prompt: str, user_prompt: str, model_name: str | None = None) -> str:
        self.ensure_configured()
        payload = {
            "modelUri": self.model_uri("gpt", model_name or self.settings.yandex_chat_model),
            "completionOptions": {
                "stream": False,
                "temperature": self.settings.model_temperature,
                "maxTokens": str(self.settings.model_max_output_tokens),
            },
            "messages": [
                {"role": "system", "text": system_prompt},
                {"role": "user", "text": user_prompt},
            ],
        }
        data = self.post_json(f"{self.settings.yandex_foundation_base_url}/completion", payload)
        alternatives = data.get("result", {}).get("alternatives", []) or data.get("alternatives", [])
        if not alternatives:
            return ""
        message = alternatives[0].get("message", {})
        return str(message.get("text", ""))

    def complete_json(self, system_prompt: str, user_prompt: str, schema: dict[str, Any], model_name: str | None = None) -> dict[str, Any]:
        schema_prompt = json.dumps(schema, ensure_ascii=False)
        text = self.complete_text(
            system_prompt,
            f"{user_prompt}\n\nВерни только валидный JSON по этой JSON Schema:\n{schema_prompt}",
            model_name,
        )
        return json.loads(extract_json_object(text))

    def post_json(self, url: str, payload: dict[str, Any]) -> dict[str, Any]:
        with httpx.Client(timeout=self.settings.model_request_timeout_seconds) as client:
            response = client.post(
                url,
                headers={
                    "Authorization": f"Api-Key {self.settings.yandex_api_key}",
                    "Content-Type": "application/json",
                },
                json=payload,
            )
            response.raise_for_status()
            return response.json()

    def model_uri(self, prefix: str, model_name: str) -> str:
        if "://" in model_name:
            return model_name
        suffix = "" if model_name.endswith("/") else "/latest"
        if prefix == "emb" and model_name.startswith("text-embeddings-v2"):
            suffix = ""
        return f"{prefix}://{self.settings.yandex_folder_id}/{model_name}{suffix}"

    def ensure_configured(self) -> None:
        if not self.is_configured:
            raise RuntimeError("Yandex provider is not configured")


def extract_json_object(text: str) -> str:
    stripped = text.strip()
    if stripped.startswith("```"):
        stripped = stripped.strip("`")
        if stripped.lower().startswith("json"):
            stripped = stripped[4:].strip()
    start = stripped.find("{")
    end = stripped.rfind("}")
    if start < 0 or end < start:
        raise ValueError("Model response does not contain a JSON object")
    return stripped[start : end + 1]
