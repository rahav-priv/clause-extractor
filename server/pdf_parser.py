import io
import pdfplumber


def extract_text_from_pdf(file_bytes: bytes) -> str:
    """Extract plain text from PDF bytes using pdfplumber.

    Pages are joined with double newlines.  Returns an empty string if
    no text could be extracted (e.g. scanned image-only PDF).
    """
    text_parts: list[str] = []

    with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
        for page in pdf.pages:
            text = page.extract_text()
            if text and text.strip():
                text_parts.append(text.strip())

    return "\n\n".join(text_parts)
