import json
from collections.abc import Iterator

import httpx
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pgvector import Vector
from psycopg.rows import dict_row
from pydantic import BaseModel
from .. import llm
from ..config import get_settings
from ..db import pool
from ..embeddings import embed_query

router = APIRouter()


class Question(BaseModel):
    question: str


def _search(question: str) -> list[dict]:
    #<=> je kosinusna distanca, pa je slicnost 1 - distanca
    vector = Vector(embed_query(question))
    with pool.connection() as conn, conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            "SELECT d.id AS document_id, d.title, c.ordinal, c.content,"
            " 1 - (c.embedding <=> %s) AS score"
            " FROM chunks c JOIN documents d ON d.id = c.document_id"
            " ORDER BY c.embedding <=> %s LIMIT %s",
            (vector, vector, get_settings().top_k),
        )
        return cur.fetchall()


def _line(payload: dict) -> str:
    return json.dumps(payload, ensure_ascii=False, default=str) + "\n"


@router.post("/ask")
def ask(payload: Question):
    question = payload.question.strip()
    if not question:
        raise HTTPException(422, "Pitanje je prazno")

    sources = _search(question)
    if not sources:
        raise HTTPException(409, "Nema dokumenata u bazi")

    if not llm.is_available():
        raise HTTPException(503, "Ollama nije dostupna")

    context = "\n\n---\n\n".join(
        f"[{index}] {source['title']}: {source['content']}"
        for index, source in enumerate(sources, start=1)
    )

    def events() -> Iterator[str]:
        yield _line(
            {
                "type": "sources",
                "sources": [
                    {
                        "index": index,
                        "document_id": source["document_id"],
                        "title": source["title"],
                        "ordinal": source["ordinal"],
                        "score": round(source["score"], 4),
                        "preview": source["content"][:200],
                    }
                    for index, source in enumerate(sources, start=1)
                ],
            }
        )

        #posle prvog reda je 200 vec poslat, pa greska mora da ide kao red u streamu
        try:
            for piece in llm.stream_answer(question, context):
                yield _line({"type": "token", "text": piece})
        except (httpx.HTTPError, ValueError) as exc:
            yield _line({"type": "error", "message": f"Greska pri generisanju: {exc}"})

        yield _line({"type": "done"})

    return StreamingResponse(events(), media_type="application/x-ndjson")
