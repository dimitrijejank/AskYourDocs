from fastapi import APIRouter, HTTPException, UploadFile
from pgvector import Vector
from ..chunking import chunk
from ..embeddings import embed
from ..db import pool
from ..extract import extract, is_supported

router = APIRouter()


@router.post("/documents",status_code=201)
def upload_document(file: UploadFile):
    if not file.filename or not is_supported(file.filename):
        raise HTTPException(415, "Podrazi formati su: pdf, docx, txt, md")

    data = file.file.read()
    text, source_type = extract(file.filename,data)
    if not text:
        raise HTTPException(422, "Dokument ne sadrzi tekst")

    contents = chunk(text)
    vectors = embed(contents)

    with pool.connection() as conn, conn.cursor() as cur:
        cur.execute(
            "INSERT INTO documents (title, source_type, byte_size, chunk_count)"
            " VALUES (%s, %s, %s, %s) RETURNING id",
            (file.filename, source_type, len(data), len(contents))
        )
        document_id = cur.fetchone()[0]
        cur.executemany(
            "INSERT INTO chunks (document_id, ordinal, content, embedding)"
            " VALUES (%s,%s,%s,%s)",
            [
                (document_id, ordinal, content, Vector(vector))
                for ordinal, (content, vector) in enumerate(zip(contents, vectors, strict=True))
            ],
        )

    return {
        "id": document_id,
        "title": file.filename,
        "source_type": source_type,
        "chunk_count": len(contents),
    }