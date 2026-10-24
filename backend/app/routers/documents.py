from uuid import UUID

from fastapi import APIRouter, HTTPException, UploadFile
from pgvector import Vector
from psycopg.rows import dict_row
from pydantic import BaseModel, Field

from ..chunking import chunk
from ..db import pool
from ..embeddings import embed
from ..extract import extract, is_supported, normalize

router = APIRouter()

#gornja granica da jedan zahtev ne pojede memoriju i ne odvali racun na OpenAI
MAX_BYTES = 10 * 1024 * 1024
MAX_CHARS = 200_000


class TextDocument(BaseModel):
    content: str = Field(max_length=MAX_CHARS)
    title: str = "Zalepljen tekst"


def _store(title: str, source_type: str, byte_size: int, text: str) -> dict:
    contents = chunk(text)
    vectors = embed(contents)

    with pool.connection() as conn, conn.cursor() as cur:
        cur.execute(
            "INSERT INTO documents (title, source_type, byte_size, chunk_count)"
            " VALUES (%s, %s, %s, %s) RETURNING id",
            (title, source_type, byte_size, len(contents)),
        )
        document_id = cur.fetchone()[0]
        cur.executemany(
            "INSERT INTO chunks (document_id, ordinal, content, embedding)"
            " VALUES (%s, %s, %s, %s)",
            [
                (document_id, ordinal, content, Vector(vector))
                for ordinal, (content, vector) in enumerate(zip(contents, vectors, strict=True))
            ],
        )

    return {
        "id": document_id,
        "title": title,
        "source_type": source_type,
        "chunk_count": len(contents),
    }


@router.post("/documents", status_code=201)
def upload_document(file: UploadFile):
    if not file.filename or not is_supported(file.filename):
        raise HTTPException(415, "Podrzani formati su: pdf, docx, txt, md")

    data = file.file.read()
    if len(data) > MAX_BYTES:
        raise HTTPException(413, "Fajl je veci od 10 MB")

    #ekstenzija je prosla, ali sadrzaj moze biti pokvaren - to je greska korisnika, ne servera
    try:
        text, source_type = extract(file.filename, data)
    except Exception:
        raise HTTPException(422, "Fajl se ne moze procitati")

    if not text:
        raise HTTPException(422, "Dokument ne sadrzi tekst")

    return _store(file.filename, source_type, len(data), text)


@router.post("/documents/text", status_code=201)
def create_text_document(payload: TextDocument):
    text = normalize(payload.content)
    if not text:
        raise HTTPException(422, "Tekst je prazan")

    return _store(payload.title, "text", len(payload.content.encode()), text)


@router.get("/documents")
def list_documents() -> list[dict]:
    with pool.connection() as conn, conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            "SELECT id, title, source_type, byte_size, chunk_count, created_at"
            " FROM documents ORDER BY created_at DESC"
        )
        return cur.fetchall()


@router.delete("/documents/{document_id}", status_code=204)
def delete_document(document_id: UUID) -> None:
    with pool.connection() as conn, conn.cursor() as cur:
        cur.execute("DELETE FROM documents WHERE id = %s", (document_id,))
        if cur.rowcount == 0:
            raise HTTPException(404, "Dokument ne postoji")
