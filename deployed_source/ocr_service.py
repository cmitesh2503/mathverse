import io

from pypdf import PdfReader


class OCRService:

    def extract_text(
        self,
        pdf_bytes: bytes
    ) -> str:

        pdf = PdfReader(
            io.BytesIO(pdf_bytes)
        )

        pages = []

        for page in pdf.pages:

            pages.append(
                page.extract_text() or ""
            )

        return "\n".join(
            pages
        )