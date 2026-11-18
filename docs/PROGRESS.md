# Starea proiectului

Fișier actualizat la fiecare pull request. Planul are 15 PR-uri, câte unul pe zi.

## Plan

| PR | Conținut | Stare |
|----|----------|-------|
| 1 | Schelet: API cu verificări de sănătate, PostgreSQL + pgvector în Docker Compose, teste, CI | ✅ pe `main` |
| 2 | Ingestie: surse, extragere pe pagini, normalizare, fragmentare, stocare idempotentă, migrări | ✅ pe `main` |
| 3 | Interfața de embeddings + Voyage AI + embedder simulat pentru teste | în review |
| 4 | Coloana de vectori + calcularea embeddings pe loturi, idempotent | |
| 5 | Endpoint de căutare semantică, cu filtre pe companie și an | |
| 6 | Interfața de LLM + furnizorul ales + LLM simulat | |
| 7 | Răspuns cu citări și refuz; citări verificate în cod | |
| 8 | Răspuns transmis în flux (streaming) | |
| 9 | Setul de evaluare + metrici (hit rate, MRR) + scor de bază | |
| 10 | Curățarea textului (numerele de pagină din fragmente) + reindexare, impact măsurat | |
| 11 | Căutare lexicală (full-text în română) | |
| 12 | Căutare hibridă cu RRF + comparație cu scorul de bază | |
| 13 | Tool calling: calculator și căutare, cu limită de pași | |
| 14 | Urmărirea costului și a latenței + teste de prompt injection | |
| 15 | Interfață de chat, evaluare în CI, README final, `INTERVIEW.md` | |

## Corpus

Rapoartele anuale 2024 și 2025 ale Băncii Transilvania (TLV), Hidroelectrica (H2O) și MedLife (M),
în română: 6 documente, 1.927 de pagini, aproximativ 6.100 de fragmente. Lista e în
`corpus/sources.yaml`; PDF-urile se descarcă în `data/raw/` (cele de la BT, de mână).

## Decizii luate

| Decizie | ADR |
|---------|-----|
| Vectorii se țin în PostgreSQL cu pgvector | [0001](adr/0001-postgresql-with-pgvector.md) |
| Fragmente pe propoziții, în cadrul unei singure pagini, măsurate în cuvinte (200 / 40) | [0002](adr/0002-page-aware-sentence-chunking.md) |
| Migrări în SQL simplu, aplicate de un runner propriu | [0003](adr/0003-plain-sql-migrations.md) |
| Embeddings cu Voyage AI `voyage-4` (1024 dimensiuni), în spatele unei interfețe | [0004](adr/0004-voyage-embeddings-behind-an-interface.md) |

## Decizii deschise

| Decizie | Necesară până la |
|---------|------------------|
| Furnizorul de LLM | PR 6 |
| Metoda de evaluare a răspunsurilor | PR 9 |

## Limite cunoscute

- Numărul paginii apare la începutul fragmentelor (se rezolvă în PR 10).
- Tabelele își pierd structura la extragere (ADR 0002).
- Aproximativ 5% din paginile Hidroelectrica sunt grafice fără text.

## Rezultate de evaluare

Încă nu există măsurători.
