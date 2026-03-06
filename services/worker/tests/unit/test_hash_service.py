import pytest
from src.services.hash_service import HashService


class TestHashService:
    @pytest.mark.parametrize(
        "input_text, expected_hash",
        [
            (
                "Hello World",
                "a591a6d40bf420404a011733cfb7b190d62c65bf0bcda32b57b277d9ad9f146e",
            ),
            (
                "Jan Kowalski CV",
                "179499c31d03728537017ffb16a1cee2991e3a9f852e5a7fa5db4c6fa163dd8e",
            ),
        ],
    )
    def test_generate_text_hash_known_values(self, input_text, expected_hash):
        assert HashService.generate_text_hash(input_text) == expected_hash

    @pytest.mark.parametrize("invalid_input", ["", "   ", None])
    def test_generate_text_hash_empty_input_raises_error(self, invalid_input):
        with pytest.raises(ValueError, match="Cannot generate hash for empty text."):
            HashService.generate_text_hash(invalid_input)

    def test_hash_consistency(self):
        text = "Experienced Python Developer with AWS skills."
        hash1 = HashService.generate_text_hash(text)
        hash2 = HashService.generate_text_hash(text)

        assert hash1 == hash2
        assert len(hash1) == 64

    def test_hash_uniqueness(self):
        text1 = "Experienced Python Developer with AWS skills."
        text2 = "Experienced Python Developer with Azure skills."

        assert HashService.generate_text_hash(text1) != HashService.generate_text_hash(
            text2
        )

    def test_hash_unicode_characters(self):
        text = "Zażółć gęślą jaźń"
        result = HashService.generate_text_hash(text)

        assert isinstance(result, str)
        assert len(result) == 64
