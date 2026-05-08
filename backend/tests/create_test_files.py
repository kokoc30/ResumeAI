"""Generate small test resume files (PDF and DOCX) for validation.

Run once:  python tests/create_test_files.py
Creates:   tests/fixtures/sample_resume.pdf
           tests/fixtures/sample_resume.docx
"""

import os

import fitz  # PyMuPDF
from docx import Document

FIXTURES_DIR = os.path.join(os.path.dirname(__file__), "fixtures")

SAMPLE_TEXT = (
    "Jane Doe\n"
    "Software Engineer\n\n"
    "Skills: Python, FastAPI, Docker, PostgreSQL\n\n"
    "Experience:\n"
    "- Built REST APIs serving 10k+ requests per day.\n"
    "- Designed microservice architecture for payment processing.\n"
    "- Wrote automated tests with pytest and CI/CD pipelines.\n\n"
    "Education:\n"
    "B.S. Computer Science, Example University, 2020\n"
)


def create_pdf(path: str) -> None:
    """Create a small single-page PDF with sample resume text."""
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((72, 72), SAMPLE_TEXT, fontsize=11)
    doc.save(path)
    doc.close()
    print(f"Created {path}")


def create_docx(path: str) -> None:
    """Create a small DOCX with sample resume text."""
    doc = Document()
    for line in SAMPLE_TEXT.strip().split("\n"):
        doc.add_paragraph(line)
    doc.save(path)
    print(f"Created {path}")


if __name__ == "__main__":
    os.makedirs(FIXTURES_DIR, exist_ok=True)
    create_pdf(os.path.join(FIXTURES_DIR, "sample_resume.pdf"))
    create_docx(os.path.join(FIXTURES_DIR, "sample_resume.docx"))
    print("Done.")
