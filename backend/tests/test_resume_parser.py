"""Unit tests for app.resume_parser module."""

import os
import pytest

from app.resume_parser import (
    extract_resume_text,
    extract_text_from_docx,
    extract_text_from_pdf,
)

FIXTURES_DIR = os.path.join(os.path.dirname(__file__), "fixtures")
PDF_PATH = os.path.join(FIXTURES_DIR, "sample_resume.pdf")
DOCX_PATH = os.path.join(FIXTURES_DIR, "sample_resume.docx")


# ---- PDF tests ----

def test_pdf_extraction_returns_text():
    with open(PDF_PATH, "rb") as f:
        text = extract_text_from_pdf(f.read())
    assert "Jane Doe" in text
    assert "Python" in text
    assert "FastAPI" in text


def test_pdf_extraction_empty_raises():
    """An empty byte string is not a valid PDF and should raise."""
    with pytest.raises((ValueError, Exception)):
        extract_text_from_pdf(b"")


# ---- DOCX tests ----

def test_docx_extraction_returns_text():
    with open(DOCX_PATH, "rb") as f:
        text = extract_text_from_docx(f.read())
    assert "Jane Doe" in text
    assert "Python" in text
    assert "FastAPI" in text


def test_docx_extraction_empty_raises():
    """Random bytes are not a valid DOCX and should raise."""
    with pytest.raises(Exception):
        extract_text_from_docx(b"not a docx")


# ---- Router function tests ----

def test_router_pdf():
    with open(PDF_PATH, "rb") as f:
        text = extract_resume_text(f.read(), "resume.pdf")
    assert "Jane Doe" in text


def test_router_docx():
    with open(DOCX_PATH, "rb") as f:
        text = extract_resume_text(f.read(), "my_resume.DOCX")
    assert "Jane Doe" in text


def test_router_unsupported_extension():
    with pytest.raises(ValueError, match="Unsupported file type"):
        extract_resume_text(b"data", "notes.txt")


def test_router_no_extension():
    with pytest.raises(ValueError, match="Unsupported file type"):
        extract_resume_text(b"data", "resume")
