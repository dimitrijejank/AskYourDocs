from .config import get_settings

BREAKS = ("\n\n", "\n", ". ")

def _find_break(text:str, start:int, end: int) -> int:
    floor = start + (end - start) // 2
    for marker in BREAKS:
        found = text.rfind(marker, floor, end)
        if found != -1:
            return found + len(marker)
    return end

def _word_start(text: str, index: int) -> int:
    space = text.find(" ", index)
    return index if space == -1 else space + 1

def chunk(text: str, size: int | None = None, overlap: int | None=None) -> list[str]:
    settings = get_settings()
    if size is None:
        size = settings.chunk_size
    if overlap is None:
        overlap = settings.chunk_overlap

    pieces = []
    start = 0
    while start < len(text):
        end = start + size
        if end >= len(text):
            pieces.append(text[start:])
            break
        end = _find_break(text,start,end)
        if len(text) - end < size // 4:
            pieces.append(text[start:])
            break
        pieces.append(text[start:end])
        start = _word_start(text, end - overlap)
    return [p.strip() for p in pieces if p.strip()]