# 0004. Voyage AI embeddings behind a provider interface

- Status: accepted
- Date: 2026-11-18

## Context

Retrieval compares a question with passages by turning both into vectors (embeddings). The
corpus is about 6,100 Romanian passages, roughly 2 million tokens. The model must handle
Romanian, be cheap enough to re-index several times while tuning, and must not make the
test suite depend on the network or on a paid account.

## Decision

- Use Voyage AI `voyage-4` through its REST API, with 1024-dimensional vectors.
- Embed passages with `input_type="document"` and questions with `input_type="query"`, so
  the model can account for the different shape of a question and the passage answering it.
- Hide the provider behind a small `Embedder` interface (`embed_documents`, `embed_query`).
- Provide a deterministic `FakeEmbedder` (hashed bag of words) for tests and offline work.
- Send passages in batches, retry on rate limits and server errors with exponential backoff
  and jitter, and fail immediately on an invalid key.

## Alternatives considered

- **A local open-source model (e.g. multilingual-e5).** Free and fully reproducible, but the
  first indexing would take tens of minutes on a laptop CPU and the Docker image would grow
  by several GB.
- **OpenAI `text-embedding-3-small`.** Cheaper per token after free usage, but requires
  pre-paid credit; Voyage's free allowance (200M tokens per account) covers this project.
- **Google `gemini-embedding-001` free tier.** Request-per-day limits would make indexing slow.
- **The official `voyageai` SDK.** Would hide the HTTP request; one endpoint does not justify a
  dependency, and the raw call is easier to explain.

## Consequences

- Indexing needs an API key and network access; tests and CI do not.
- Vectors from different models or dimensions are not comparable: changing the model means
  re-embedding every passage. The model name is stored with the vectors (next PR) to detect it.
- Passages are sent to a third-party service. They are public annual reports, so this is
  acceptable here; it would not be for confidential documents.
- The fake embedder only measures shared words; it is not a stand-in for retrieval quality.
