import hashlib


class HashService:
    @staticmethod
    def generate_text_hash(text: str) -> str:
        if not text or not text.strip():
            raise ValueError("Cannot generate hash for empty text.")
        return hashlib.sha256(text.encode("utf-8")).hexdigest()
