-- One embedding per chunk. The dimension must match EMBEDDING_DIMENSIONS (1024 for voyage-4);
-- changing it needs a new migration.
ALTER TABLE chunks
    ADD COLUMN embedding       vector(1024),
    ADD COLUMN embedding_model TEXT,
    ADD COLUMN embedded_at     TIMESTAMPTZ;

-- A vector is meaningless without the model that produced it: vectors from different models
-- cannot be compared. Either both are set or neither is.
ALTER TABLE chunks
    ADD CONSTRAINT chunks_embedding_has_model
    CHECK ((embedding IS NULL) = (embedding_model IS NULL));
