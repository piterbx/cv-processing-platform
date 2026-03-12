import logging
from typing import Any

from ollama import AsyncClient
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

logger = logging.getLogger(__name__)


class VectorService:
    @staticmethod
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=2, min=2, max=10),
        retry=retry_if_exception_type(Exception),
        reraise=True,
    )
    async def generate_embedding_with_retry(
        text: str, host: str, model_name: str
    ) -> list[float] | None:
        return await VectorService._execute_request(text, host, model_name)

    @staticmethod
    async def generate_embedding(
        text: str, host: str, model_name: str
    ) -> list[float] | None:
        try:
            return await VectorService._execute_request(text, host, model_name)
        except Exception as e:
            logger.error(
                "Failed to generate embedding via Ollama: %s", e, exc_info=True
            )
            return None

    @staticmethod
    async def _execute_request(
        text: str, host: str, model_name: str
    ) -> list[float] | None:
        if not text or not text.strip():
            logger.warning("Empty text provided for vectorization.")
            return None

        client = AsyncClient(host=host)
        response = await client.embeddings(model=model_name, prompt=text)

        return response.get("embedding")

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
