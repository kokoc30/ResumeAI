import pytest
from app.chunker import chunk_resume_text, detect_section_heading, split_long_text, ResumeChunk

def test_detect_section_heading():
    assert detect_section_heading("Education") == "Education"
    assert detect_section_heading("WORK EXPERIENCE") == "Work Experience"
    assert detect_section_heading("Skills:") == "Skills"
    assert detect_section_heading("Some random line that is definitely not a heading") is None
    assert detect_section_heading("Summary ") == "Summary"

def test_split_long_text():
    short_text = "This is a short text."
    assert split_long_text(short_text, max_chars=50) == [short_text]

    long_text = "This is sentence one. This is sentence two. This is sentence three."
    chunks = split_long_text(long_text, max_chars=30)
    assert len(chunks) > 1
    assert "sentence one" in chunks[0]

def test_chunk_empty_text():
    with pytest.raises(ValueError, match="Resume text is empty"):
        chunk_resume_text("   ")

def test_chunk_short_text():
    with pytest.raises(ValueError, match="too short to chunk"):
        chunk_resume_text("Too short.")

def test_chunk_resume_text_with_sections_large():
    resume = (
        "John Doe - Software Engineer\n"
        "Summary\n"
        "I am a highly skilled software engineer with 5 years of experience building web applications. "
        "I love Python and making fast backends.\n"
        "Skills\n"
        "Python, FastAPI, SQL, Docker, AWS, React, JavaScript, HTML, CSS, Git, Linux, Bash.\n"
        "Experience\n"
        "Software Engineer at Company A. I was responsible for building the core API using FastAPI and PostgreSQL. "
        "I also managed Docker containers."
    )
    
    chunks = chunk_resume_text(resume)
    
    assert len(chunks) > 0
    sections_found = {c.section for c in chunks}
    assert "Summary" in sections_found
    assert "Skills" in sections_found
    assert "Experience" in sections_found

    for c in chunks:
        assert isinstance(c, ResumeChunk)
        assert c.chunk_id.startswith("chunk_")
        assert len(c.text) >= 40

def test_chunk_paragraph_fallback():
    # No headings, just long text
    para1 = "This is a long paragraph about my experience. " * 5
    para2 = "Here is another long paragraph about my projects. " * 5
    para3 = "Finally, here is some text about my education and skills. " * 5
    
    resume = f"{para1}\n\n{para2}\n\n{para3}"
    chunks = chunk_resume_text(resume)
    
    assert len(chunks) > 0
    assert all(c.section is None for c in chunks)
    for i, c in enumerate(chunks):
        assert c.chunk_index == i
        assert len(c.text) >= 40
