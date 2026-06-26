"""
Raw text extraction for supported upload types: PDF, TXT, MD.
Each function takes a file-like object (as Streamlit's file_uploader
provides) or a path, and returns plain extracted text.
"""

from typing import Union, BinaryIO
import pdfplumber


def extract_from_pdf(file: Union[str, BinaryIO]) -> str:
    """Extracts text from a PDF, page by page, joined with newlines."""
    text_chunks = []
    with pdfplumber.open(file) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                text_chunks.append(page_text)
    return "\n".join(text_chunks)


def extract_from_txt(file: Union[str, BinaryIO]) -> str:
    """Reads a plain text file. Accepts a path or a file-like object."""
    if hasattr(file, "read"):
        content = file.read()
        return content.decode("utf-8") if isinstance(content, bytes) else content
    with open(file, "r", encoding="utf-8") as f:
        return f.read()


def extract_from_markdown(file: Union[str, BinaryIO]) -> str:
    """
    Markdown is treated as plain text for extraction purposes —
    we don't strip formatting because headers/bullets often carry
    useful structure (e.g. "## Tools Used").
    """
    return extract_from_txt(file)


def extract_text(filename: str, file: Union[str, BinaryIO]) -> str:
    """
    Dispatches to the right extractor based on file extension.
    Raises ValueError for unsupported types.
    """
    lower = filename.lower()
    if lower.endswith(".pdf"):
        return extract_from_pdf(file)
    elif lower.endswith(".txt"):
        return extract_from_txt(file)
    elif lower.endswith(".md"):
        return extract_from_markdown(file)
    else:
        raise ValueError(f"Unsupported file type: {filename}")