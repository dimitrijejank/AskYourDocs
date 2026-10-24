import io
import re
from pathlib import Path
from docx import Document
from pypdf import PdfReader

SUPPORTED: dict[str,str] = {
    ".pdf": "pdf",
    ".docx": "docx",
    ".txt": "txt",
    ".md": "md"
    }

def is_supported(filename: str) -> bool:
    return Path(filename).suffix.lower() in SUPPORTED

def normalize(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r","\n")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()

def _read_pdf(data: bytes) -> str:
    reader = PdfReader(io.BytesIO(data))
    pages = [page.extract_text() or "" for page in reader.pages]
    return "\n\n".join(pages)

def _read_docx(data: bytes) -> str:
    document = Document(io.BytesIO(data))
    return "\n\n".join(p.text for p in document.paragraphs if p.text.strip())

def _read_plain(data: bytes) -> str:
    return data.decode("utf-8-sig", errors="replace")

def extract(filename: str, data:bytes) -> tuple[str,str]:
    source_type = SUPPORTED[Path(filename).suffix.lower()]
    if source_type == "pdf":
        raw = _read_pdf(data)
    elif source_type == "docx":
        raw = _read_docx(data)
    else: 
        raw = _read_plain(data)
    return normalize(raw), source_type
