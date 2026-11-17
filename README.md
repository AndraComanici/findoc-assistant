# FinDoc Assistant

Question answering over the annual reports of companies listed on the Bucharest Stock Exchange.
Every answer cites the page it comes from, and the assistant says so when the documents do not
contain the answer.

> Work in progress. This README grows with the project; see [docs/PROGRESS.md](docs/PROGRESS.md)
> for the current status (in Romanian).

## Stack

Python · FastAPI · PostgreSQL + pgvector · pypdf · Docker Compose · GitHub Actions

## Run it locally

Requirements: Docker Desktop and Git.

```bash
cp .env.example .env
docker compose up --build
```

Then open:

- http://localhost:8000/health – the API process is up
- http://localhost:8000/health/ready – the API can reach the database and pgvector is installed
- http://localhost:8000/docs – interactive API documentation

Stop with `Ctrl+C`. To also delete the database volume: `docker compose down -v`.

## Load the documents

The assistant answers from the annual reports listed in [corpus/sources.yaml](corpus/sources.yaml).
The PDFs are not stored in this repository.

1. Download each report from the company's investor relations page and save it in `data/raw/`
   under the file name given in `sources.yaml` (for example `data/raw/tlv-2025.pdf`).
   Entries that have a `url` can be downloaded automatically:

   ```bash
   docker compose run --rm api python -m app.cli download
   ```

2. With the stack running, extract, split and store the documents:

   ```bash
   docker compose run --rm api python -m app.cli ingest
   ```

   Ingestion is idempotent: a file that has not changed is skipped. Use `--force` to
   re-process everything, or `--only tlv-2025` to process a single document.

## Run the tests

Requirements: Python 3.12 or newer.

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
ruff check .
pytest
```

Integration tests need a PostgreSQL database with pgvector. They run in CI; locally, point
`TEST_DATABASE_URL` at an empty database and run `pytest -m integration`. The tests drop and
recreate the tables, so never use a database whose data you want to keep.

## Project layout

```
app/                 application code (FastAPI)
app/ingestion/       PDF extraction, text normalisation, chunking, storage
corpus/              list of source documents
data/raw/            downloaded PDFs (not committed)
db/init/             SQL run when the database volume is first created
db/migrations/       schema migrations, applied in order by `python -m app.cli migrate`
tests/               automated tests
docs/adr/            architecture decision records
.github/workflows/   continuous integration
```

## Architecture decisions

Decisions are recorded in [docs/adr](docs/adr), one file per decision.

## Disclaimer

The assistant summarises public documents. It does not give investment advice.
