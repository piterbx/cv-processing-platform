import asyncio
import logging

import fitz  # PyMuPDF

logger = logging.getLogger(__name__)


class PDFService:
    @staticmethod
    def _extract_sync(file_path: str) -> str:
        """
        Private synchronous function performing CPU-bound PDF extraction.
        Uses block extraction to correctly handle multi-column resumes.
        """
        try:
            doc = fitz.open(file_path)
            extracted_blocks = []

            for page in doc:
                # get_text("blocks") prevents merging text across columns
                for block in page.get_text("blocks"):
                    text_content = block[4].strip()
                    if text_content:
                        extracted_blocks.append(text_content)

            doc.close()
            return "\n\n".join(extracted_blocks)

        except Exception as e:
            logger.error("Failed to parse PDF at %s: %s", file_path, e, exc_info=True)
            raise ValueError(f"Document parsing error: {str(e)}") from e

    @staticmethod
    async def extract_text(file_path: str) -> str:
        """
        Public asynchronous wrapper.
        Offloads the CPU-heavy extraction to a separate thread
        to avoid blocking the event loop.
        """
        return await asyncio.to_thread(PDFService._extract_sync, file_path)
