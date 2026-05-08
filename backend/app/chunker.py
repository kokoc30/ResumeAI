"""Text chunking helpers."""

import re
from dataclasses import dataclass

@dataclass
class ResumeChunk:
    chunk_id: str
    text: str
    section: str | None
    chunk_index: int


# Common resume section headings
SECTION_HEADINGS = {
    "summary",
    "objective",
    "education",
    "skills",
    "technical skills",
    "projects",
    "experience",
    "work experience",
    "professional experience",
    "certifications",
    "awards",
    "activities",
    "leadership"
}

def detect_section_heading(line: str) -> str | None:
    """Detect if a line is a likely section heading."""
    clean_line = line.strip().lower().rstrip(":")
    if len(clean_line) < 40 and clean_line in SECTION_HEADINGS:
        return clean_line.title()
    return None

def split_long_text(text: str, max_chars: int = 1000) -> list[str]:
    """Split text that is too long into smaller chunks, trying not to break sentences."""
    if len(text) <= max_chars:
        return [text]

    chunks = []
    paragraphs = re.split(r'\n\s*\n', text)
    
    current_chunk = []
    current_length = 0
    
    for para in paragraphs:
        if not para.strip():
            continue
            
        # If the paragraph itself is too long, we need to split it by sentences
        if len(para) > max_chars:
            sentences = re.split(r'(?<=[.!?])\s+', para)
            for sentence in sentences:
                if not sentence.strip():
                    continue
                if current_length + len(sentence) > max_chars and current_chunk:
                    chunks.append(" ".join(current_chunk).strip())
                    current_chunk = [sentence]
                    current_length = len(sentence)
                else:
                    current_chunk.append(sentence)
                    current_length += len(sentence) + 1 # +1 for space
        else:
            if current_length + len(para) > max_chars and current_chunk:
                chunks.append("\n\n".join(current_chunk).strip())
                current_chunk = [para]
                current_length = len(para)
            else:
                current_chunk.append(para)
                current_length += len(para) + 2 # +2 for newlines

    if current_chunk:
        chunks.append("\n\n".join(current_chunk).strip())
        
    return chunks

def chunk_resume_text(text: str) -> list[ResumeChunk]:
    """Split resume text into section-based chunks."""
    if not text or not text.strip():
        raise ValueError("Resume text is empty.")
        
    clean_text = text.strip()
    if len(clean_text) < 40:
        raise ValueError("Resume text is too short to chunk effectively.")
        
    lines = clean_text.splitlines()
    
    raw_chunks = []
    current_section = None
    current_text = []
    
    def flush_chunk(text_lines, section_name):
        chunk_content = "\n".join(text_lines).strip()
        if not chunk_content:
            return
            
        if len(chunk_content) > 1200:
            split_texts = split_long_text(chunk_content, max_chars=1000)
            for part in split_texts:
                if len(part.strip()) >= 40:
                    raw_chunks.append((part.strip(), section_name))
        elif len(chunk_content) >= 40:
            raw_chunks.append((chunk_content, section_name))

    for line in lines:
        if not line.strip():
            current_text.append(line)
            continue
            
        heading = detect_section_heading(line)
        if heading:
            flush_chunk(current_text, current_section)
            current_section = heading
            current_text = [line]
        else:
            current_text.append(line)
            
    flush_chunk(current_text, current_section)

    result = []
    for i, (chunk_content, section) in enumerate(raw_chunks):
        result.append(
            ResumeChunk(
                chunk_id=f"chunk_{i}",
                text=chunk_content,
                section=section,
                chunk_index=i
            )
        )
        
    return result
