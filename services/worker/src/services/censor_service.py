import logging
import re
from re import Match

logger = logging.getLogger(__name__)


class CensorService:
    # contact Info
    EMAIL_REGEX = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,7}\b")

    # 9 digits (optionally prefixed by +48 or 48).
    # negative lookbehinds/lookaheads (?<!\d) and (?!\d) prevent it
    # from matching 10 or 11 digit numbers (like PESEL).
    PHONE_REGEX = re.compile(
        r"(?<!\d)(?:\+?48[\s\-]*)?\d{3}[\s\-]*\d{3}[\s\-]*\d{3}(?!\d)"
    )

    # general URLs
    URL_REGEX = re.compile(
        r"\b(?:https?:\/\/|www\.)[-a-zA-Z0-9@:%._\+~#=]{1,256}\.[a-zA-Z0-9()]{1,6}\b(?:[-a-zA-Z0-9()@:%_\+.~#?&\/=]*)",
        re.IGNORECASE,
    )

    # Polish addresses
    POSTAL_CODE_REGEX = re.compile(
        r"\b\d{2}-\d{3}[ \t]+[A-ZĄĆĘŁŃÓŚŹŻa-ząćęłńóśźż]+"
        r"(?:[ \t]+[A-ZĄĆĘŁŃÓŚŹŻa-ząćęłńóśźż]+)*\b"
    )
    STREET_REGEX = re.compile(
        r"\b(?:ul\.|al\.|pl\.|os\.)[ \t]+[A-ZĄĆĘŁŃÓŚŹŻa-ząćęłńóśźż \t]+?"
        r"\d+[a-zA-Z]?(?:[ \t]*[/\\\-][ \t]*\d+)?\b",
        re.IGNORECASE,
    )

    # PESEL
    PESEL_CANDIDATE_REGEX = re.compile(r"\b\d{11}\b")

    @staticmethod
    def _is_valid_pesel(pesel: str) -> bool:
        weights = [1, 3, 7, 9, 1, 3, 7, 9, 1, 3]
        try:
            checksum = sum(int(pesel[i]) * weights[i] for i in range(10))
            return (10 - (checksum % 10)) % 10 == int(pesel[10])
        except ValueError:
            return False

    @staticmethod
    def _censor_pesel(match: Match) -> str:
        pesel = match.group(0)
        if CensorService._is_valid_pesel(pesel):
            return "[PESEL_REMOVED]"
        return pesel

    @staticmethod
    def anonymize_text(raw_text: str) -> str:
        if not raw_text:
            return ""

        try:
            text = CensorService.URL_REGEX.sub("[URL_REMOVED]", raw_text)
            text = CensorService.EMAIL_REGEX.sub("[EMAIL_REMOVED]", text)
            text = CensorService.PHONE_REGEX.sub("[PHONE_REMOVED]", text)
            text = CensorService.STREET_REGEX.sub("[ADDRESS_REMOVED]", text)
            text = CensorService.POSTAL_CODE_REGEX.sub("[ADDRESS_REMOVED]", text)
            text = CensorService.PESEL_CANDIDATE_REGEX.sub(
                CensorService._censor_pesel, text
            )
            return text
        except Exception as e:
            logger.error(
                "Error occurred during text anonymization: %s", e, exc_info=True
            )
            raise RuntimeError(f"Smart anonymization failed: {str(e)}") from e
