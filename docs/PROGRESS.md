# Starea proiectului

Fișier actualizat la fiecare pull request.

## Livrat

| PR | Conținut | Stare |
|----|----------|-------|
| 1 | Schelet: API cu verificări de sănătate, PostgreSQL + pgvector în Docker Compose, teste, CI | în review |

## Urmează

PR 2 – Ingestie: listă de surse, descărcare, extragere de text pe pagini, fragmentare cu metadate.

## Decizii luate

| Decizie | ADR |
|---------|-----|
| Vectorii se țin în PostgreSQL cu pgvector | [0001](adr/0001-postgresql-with-pgvector.md) |

## Decizii deschise

| Decizie | Necesară până la |
|---------|------------------|
| Corpusul: ce companii și câte rapoarte | PR 2 |
| Embeddings: model local sau prin API | PR 3 |
| Furnizorul de LLM | PR 4 |
| Metoda de evaluare a răspunsurilor | PR 5 |

## Rezultate de evaluare

Încă nu există măsurători.
