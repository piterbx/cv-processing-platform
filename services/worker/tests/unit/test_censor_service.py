import pytest
from src.services.censor_service import CensorService


class TestCensorService:
    """
    Unit tests for the CensorService.
    Ensures that PII is correctly redacted
    without destroying the surrounding context of the document.
    """

    @pytest.mark.parametrize(
        "raw_text, expected_text",
        [
            ("Contact me at john.doe@example.com.", "Contact me at [EMAIL_REMOVED]."),
            ("Email: dev+test@sub.domain.co.uk", "Email: [EMAIL_REMOVED]"),
            ("a@b.com and c@d.org", "[EMAIL_REMOVED] and [EMAIL_REMOVED]"),
        ],
    )
    def test_email_redaction(self, raw_text: str, expected_text: str):
        assert CensorService.anonymize_text(raw_text) == expected_text

    @pytest.mark.parametrize(
        "raw_text, expected_text",
        [
            ("Call +48 123 456 789 today.", "Call [PHONE_REMOVED] today."),
            # dashes and no prefix
            ("Phone: 123-456-789", "Phone: [PHONE_REMOVED]"),
            # continuous string of numbers
            ("My number is 123456789.", "My number is [PHONE_REMOVED]."),
            # spacing anomalies
            ("Tel: +48  123 456 789", "Tel: [PHONE_REMOVED]"),
        ],
    )
    def test_phone_redaction(self, raw_text: str, expected_text: str):
        assert CensorService.anonymize_text(raw_text) == expected_text

    @pytest.mark.parametrize(
        "raw_text, expected_text",
        [
            ("Portfolio: https://github.com/johndoe", "Portfolio: [URL_REMOVED]"),
            ("Visit www.linkedin.com/in/johndoe-123", "Visit [URL_REMOVED]"),
            (
                "Check out https://my-blog.pl/about for info.",
                "Check out [URL_REMOVED] for info.",
            ),
        ],
    )
    def test_url_redaction(self, raw_text: str, expected_text: str):
        assert CensorService.anonymize_text(raw_text) == expected_text

    @pytest.mark.parametrize(
        "raw_text, expected_text",
        [
            # valid PESEL (checksum correct for date 90-01-01)
            ("My PESEL is 90010112349.", "My PESEL is [PESEL_REMOVED]."),
            # invalid PESEL (11 digits, but wrong checksum)
            ("Account: 12345678901.", "Account: 12345678901."),
            # too short or too long numbers shouldn't trigger the candidate regex at all
            ("ID: 1234567890", "ID: 1234567890"),
        ],
    )
    def test_smart_pesel_redaction(self, raw_text: str, expected_text: str):
        assert CensorService.anonymize_text(raw_text) == expected_text

    @pytest.mark.parametrize(
        "raw_text, expected_text",
        [
            # postal codes
            ("I live in 00-123 Warszawa.", "I live in [ADDRESS_REMOVED]."),
            ("Zip: 80-001 Gdańsk Wrzeszcz", "Zip: [ADDRESS_REMOVED]"),
            # streets
            ("Address: ul. Marszałkowska 123/45", "Address: [ADDRESS_REMOVED]"),
            ("Office at al. Jerozolimskie 12", "Office at [ADDRESS_REMOVED]"),
            ("os. Piastowskie 4A", "[ADDRESS_REMOVED]"),
        ],
    )
    def test_address_redaction(self, raw_text: str, expected_text: str):
        assert CensorService.anonymize_text(raw_text) == expected_text

    def test_mixed_realistic_resume_scenario(self):
        """
        Test representing a real CV header.
        """
        raw_cv_header = (
            "Jan Kowalski\n"
            "ul. Kwiatowa 15/2, 02-134 Warszawa\n"
            "Phone: +48 987 654 321 | Email: jan.k@gmail.com\n"
            "LinkedIn: www.linkedin.com/in/jank\n"
            "PESEL: 90010112349"
        )

        expected_cv_header = (
            "Jan Kowalski\n"
            "[ADDRESS_REMOVED], [ADDRESS_REMOVED]\n"
            "Phone: [PHONE_REMOVED] | Email: [EMAIL_REMOVED]\n"
            "LinkedIn: [URL_REMOVED]\n"
            "PESEL: [PESEL_REMOVED]"
        )

        assert CensorService.anonymize_text(raw_cv_header) == expected_cv_header

    @pytest.mark.parametrize(
        "edge_case_input, expected_output",
        [
            ("", ""),
            (None, ""),  # testing if None returns an empty string
            ("Just normal text with no PII.", "Just normal text with no PII."),
        ],
    )
    def test_edge_cases(self, edge_case_input, expected_output):
        assert CensorService.anonymize_text(edge_case_input) == expected_output
