CREATE EXTENSION IF NOT EXISTS vector;

-- One row per source document (an annual report).
CREATE TABLE documents (
    id           BIGSERIAL PRIMARY KEY,
    source_id    TEXT        NOT NULL UNIQUE,
    company      TEXT        NOT NULL,
    ticker       TEXT        NOT NULL,
    year         INT         NOT NULL CHECK (year BETWEEN 2000 AND 2100),
    title        TEXT        NOT NULL,
    source_url   TEXT,
    file_sha256  TEXT        NOT NULL,
    page_count   INT         NOT NULL CHECK (page_count >= 0),
    ingested_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- A passage of text from one page of a document. Retrieval works on chunks;
-- page_number is what answers cite.
CREATE TABLE chunks (
    id           BIGSERIAL PRIMARY KEY,
    document_id  BIGINT NOT NULL REFERENCES documents (id) ON DELETE CASCADE,
    chunk_index  INT    NOT NULL CHECK (chunk_index >= 0),
    page_number  INT    NOT NULL CHECK (page_number >= 1),
    content      TEXT   NOT NULL,
    word_count   INT    NOT NULL CHECK (word_count > 0),
    UNIQUE (document_id, chunk_index)
);
