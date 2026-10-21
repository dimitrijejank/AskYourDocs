CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE IF NOT EXISTS documents (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    title text NOT NULL,
    source_type text NOT NULL,
    byte_size integer NOT NULL DEFAULT 0,
    chunk_count integer NOT NULL DEFAULT 0,
    created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS chunks (
    id bigserial PRIMARY KEY,
    document_id uuid NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    ordinal integer NOT NULL,
    content text NOT NULL,
    embedding vector(1536) NOT NULL,
    UNIQUE (document_id, ordinal)
);

CREATE INDEX IF NOT EXISTS chunks_document_id_idx ON chunks (document_id);

CREATE INDEX IF NOT EXISTS chunks_embedding_idx ON chunks USING hnsw (embedding vector_cosine_ops);