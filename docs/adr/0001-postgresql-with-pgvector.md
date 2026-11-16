# 0001. Store embeddings in PostgreSQL with pgvector

- Status: accepted
- Date: 2026-11-16

## Context

The assistant retrieves relevant passages by comparing embedding vectors. It also needs ordinary
relational data (documents, pages, passages) and, later, keyword search over the same passages.
The corpus is small: a handful of annual reports, in the order of tens of thousands of passages.
The project is built and operated by one person.

## Decision

Use a single PostgreSQL database with the pgvector extension for both relational data and
embedding vectors.

## Alternatives considered

- **A dedicated vector database (Qdrant, Pinecone, Weaviate).** Built for very large collections
  and offers features we do not need at this size. It would add a second service to run, and
  passages would have to be kept in sync between two stores.
- **An in-memory index (FAISS) next to the application.** Fast, but nothing is persisted or
  queryable with SQL, and metadata filtering would have to be written by hand.

## Consequences

- One service to run, back up and reason about; vectors, text and metadata are updated in the
  same transaction.
- SQL filters (company, year) and PostgreSQL full-text search can be combined with vector search.
- If the corpus grows to tens of millions of passages, search latency and index build time would
  need to be measured again, and a dedicated store reconsidered.
