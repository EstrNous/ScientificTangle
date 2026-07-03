from pydantic_settings import BaseSettings


class ChatUiDbSettings(BaseSettings):
    model_config = {"env_prefix": "GATEWAY_"}

    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/chat_ui_db"

settings = ChatUiDbSettings()