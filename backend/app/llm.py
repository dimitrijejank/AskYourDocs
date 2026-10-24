import json
from collections.abc import Iterator

import httpx

from .config import get_settings

SYSTEM_PROMPT = (
    "Odgovaraj iskljucivo na osnovu prilozenih izvoda iz dokumenata."
    " Ako odgovor nije u njima, reci da ne znas."
    " Pozovi se na izvod brojem u uglastim zagradama, npr. [2]."
)


def is_available() -> bool:
    settings = get_settings()
    try:
        response = httpx.get(f"{settings.ollama_url}/api/tags", timeout=3)
    except httpx.HTTPError:
        return False
    return response.status_code == 200


def stream_answer(question: str, context: str) -> Iterator[str]:
    """Generise odgovor rec po rec iz Ollame."""
    settings = get_settings()
    payload = {
        "model": settings.ollama_model,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": f"Izvodi iz dokumenata:\n\n{context}\n\nPitanje: {question}",
            },
        ],
        "stream": True,
    }

    #kratak connect timeout, dug read jer model generise sporo
    timeout = httpx.Timeout(10.0, read=180.0)
    with httpx.stream(
        "POST", f"{settings.ollama_url}/api/chat", json=payload, timeout=timeout
    ) as response:
        response.raise_for_status()
        for line in response.iter_lines():
            if not line:
                continue
            message = json.loads(line)
            piece = message.get("message", {}).get("content", "")
            if piece:
                yield piece
            if message.get("done"):
                break
