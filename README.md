# FinDoc Assistant

Question answering over the annual reports of companies listed on the Bucharest Stock Exchange.
Every answer cites the page it comes from, and the assistant says so when the documents do not
contain the answer.

> Work in progress. This README grows with the project; see [docs/PROGRESS.md](docs/PROGRESS.md)
> for the current status (in Romanian).

## Stack

Python · FastAPI · PostgreSQL + pgvector · Docker Compose · GitHub Actions

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

## Run the tests

Requirements: Python 3.12 or newer.

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
ruff check .
pytest
```

## Project layout

```
app/                 application code (FastAPI)
tests/               automated tests
db/init/             SQL run when the database is first created
docs/adr/            architecture decision records
.github/workflows/   continuous integration
```

## Architecture decisions

Decisions are recorded in [docs/adr](docs/adr), one file per decision.

## Disclaimer

The assistant summarises public documents. It does not give investment advice.
