# 0005. Resumable, rate-limited embedding of chunks

- Status: accepted
- Date: 2026-11-20

## Context

About 6,100 chunks (roughly 2 million tokens) need an embedding. Voyage AI's free trial,
without a payment method, allows 3 requests and 10,000 tokens per minute, so a full run takes
several hours. It will be interrupted: the laptop sleeps, the network drops, the quota is hit.
Embeddings from different models cannot be compared, so the database must know which model
produced each vector.

## Decision

- Store the vector in `chunks.embedding` (`vector(1024)`) next to `embedding_model`; a check
  constraint makes both set or both empty.
- Embed in small batches and commit each batch on its own. A chunk is pending when it has no
  vector or a vector from another model, so a rerun continues where the last one stopped and a
  model change re-embeds everything.
- Stay under the provider's quota on the client side: a sliding one-minute window counts
  requests and estimated tokens and waits before a request that would exceed either limit.
  Batches are sized to at most 90% of the per-minute token budget.
- Estimate tokens as characters / 3, which over-estimates Romanian text on purpose.

## Alternatives considered

- **One long transaction for the whole corpus.** Simpler, but an interruption after three hours
  would throw away all the work.
- **Rely only on retries after HTTP 429.** Works, but every refused request still counts against
  the quota and the run degrades into a loop of failures and waits.
- **Voyage's Batch API.** Asynchronous and cheaper, but has no free tokens and adds polling.
- **Adding a payment method** (higher limits, minutes instead of hours). A cost decision for the
  owner; the code supports it by changing two settings.

## Consequences

- Indexing on the free trial takes about four hours and can be split across several sessions.
- Re-ingesting a document deletes its chunks, so the new chunks are picked up automatically.
- The token estimate is conservative, so runs are somewhat slower than the quota would allow.
- The vector dimension is fixed by the migration; another dimension needs a new migration.
