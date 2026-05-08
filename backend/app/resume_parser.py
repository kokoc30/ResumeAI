"""Resume parsing utilities.

Extracts plain text from PDF and DOCX resume files.
Does not store the file or log its content.
"""

import io

import fitz  # PyMuPDF
from docx import Document

from app.utils import clean_text


def extract_text_from_pdf(file_bytes: bytes) -> str:
    """Extract text from PDF bytes. Raises ValueError if no text found."""
    text_parts: list[str] = []

    with fitz.open(stream=file_bytes, filetype="pdf") as pdf:
        for page in pdf:
            page_text = page.get_text()
            if page_text:
                text_parts.append(page_text)

    full_text = clean_text("\n".join(text_parts))

    if not full_text:
        raise ValueError("Could not extract any text from the PDF file.")

    return full_text


def extract_text_from_docx(file_bytes: bytes) -> str:
    """Extract text from DOCX bytes. Raises ValueError if no text found."""
    doc = Document(io.BytesIO(file_bytes))

    text_parts: list[str] = [p.text for p in doc.paragraphs if p.text.strip()]

    full_text = clean_text("\n".join(text_parts))

    if not full_text:
        raise ValueError("Could not extract any text from the DOCX file.")

    return full_text


def extract_resume_text(file_bytes: bytes, filename: str) -> str:
    """Route to the correct parser based on the file extension."""
    extension = filename[filename.rfind("."):].lower() if "." in filename else ""

    if extension == ".pdf":
        return extract_text_from_pdf(file_bytes)
    elif extension == ".docx":
        return extract_text_from_docx(file_bytes)
    else:
        raise ValueError(
            f"Unsupported file type '{extension}'. "
            "Only .pdf and .docx files are accepted."
        )
