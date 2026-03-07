from common.config import BaseAppSettings


class Settings(BaseAppSettings):
    # LLM & Ollama Configuration
    LLM_MODEL: str = "gemma3:4b"


settings = Settings()
