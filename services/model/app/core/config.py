from shared.config.settings import ServiceSettings
from pydantic_settings import SettingsConfigDict


class Settings(ServiceSettings):
    service_name: str = "model"
    port: int = 8006
    llm_api_enabled: bool = False
    llm_provider: str = "yandex"
    yandex_ai_base_url: str = "https://ai.api.cloud.yandex.net/v1"
    yandex_foundation_base_url: str = "https://llm.api.cloud.yandex.net/foundationModels/v1"
    yandex_api_key: str = ""
    yandex_folder_id: str = ""
    yandex_chat_model: str = "yandexgpt-5.1"
    yandex_fast_model: str = "yandexgpt-5-lite"
    yandex_long_context_model: str = "deepseek-v4-flash"
    yandex_multilingual_model: str = "qwen3-235b-a22b-fp8"
    yandex_embedding_doc_model: str = "text-embeddings-v2-doc"
    yandex_embedding_query_model: str = "text-embeddings-v2-query"
    yandex_embedding_dim: int = 256
    yandex_use_tuned_embeddings: bool = False
    yandex_tuned_embedding_model_uri: str = ""
    model_request_timeout_seconds: float = 120.0
    model_temperature: float = 0.2
    model_max_output_tokens: int = 2000
    embedding_dimensions: int = 256
    confirmed_confidence_threshold: float = 0.72
    model_config = SettingsConfigDict(env_prefix="", env_file=".env", extra="ignore")

    @property
    def yandex_enabled(self) -> bool:
        return self.llm_provider == "yandex" and bool(self.yandex_api_key and self.yandex_folder_id)


settings = Settings()
