import logging
from typing import Any

from ollama import AsyncClient

logger = logging.getLogger(__name__)


class VectorService:
    @staticmethod
    async def generate_embedding(
        text: str, host: str, model_name: str
    ) -> list[float] | None:
        if not text or not text.strip():
            logger.warning("Empty text provided for vectorization.")
            return None

        try:
            client = AsyncClient(host=host)
            response = await client.embeddings(model=model_name, prompt=text)

            return response.get("embedding")

        except Exception as e:
            logger.error(
                "Failed to generate embedding via Ollama: %s", e, exc_info=True
            )
            return None

    @staticmethod
    def prepare_text_for_embedding(extracted_data: dict[str, Any]) -> str:
        parts = []

        def extract_strings(data: Any) -> None:
            if isinstance(data, dict):
                for key, value in data.items():
                    if key != "prompt_injection_detected":
                        extract_strings(value)
            elif isinstance(data, list):
                for item in data:
                    extract_strings(item)
            elif isinstance(data, str) and data.strip():
                parts.append(data.strip())

        extract_strings(extracted_data)
        return " ".join(parts)
