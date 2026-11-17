# Starea proiectului

Fișier actualizat la fiecare pull request.

## Livrat

| PR | Conținut | Stare |
|----|----------|-------|
| 1 | Schelet: API cu verificări de sănătate, PostgreSQL + pgvector în Docker Compose, teste, CI | pe `main` |
| 2 | Ingestie: listă de surse, extragere text pe pagini, normalizare, fragmentare, stocare, migrări | în review |

## Urmează

PR 3 – Embeddings, stocarea vectorilor și un endpoint de căutare semantică.

## Corpus

Rapoartele anuale 2024 și 2025 ale Băncii Transilvania (TLV), Hidroelectrica (H2O) și MedLife (M),
în română. Lista e în `corpus/sources.yaml`; PDF-urile se descarcă în `data/raw/`.

## Decizii luate

| Decizie | ADR |
|---------|-----|
| Vectorii se țin în PostgreSQL cu pgvector | [0001](adr/0001-postgresql-with-pgvector.md) |
| Fragmente pe propoziții, în cadrul unei singure pagini, măsurate în cuvinte (200 / 40) | [0002](adr/0002-page-aware-sentence-chunking.md) |
| Migrări în SQL simplu, aplicate de un runner propriu | [0003](adr/0003-plain-sql-migrations.md) |

## Decizii deschise

| Decizie | Necesară până la |
|---------|------------------|
| Embeddings: model local sau prin API | PR 3 |
| Furnizorul de LLM | PR 4 |
| Metoda de evaluare a răspunsurilor | PR 5 |

## Rezultate de evaluare

Încă nu există măsurători.
