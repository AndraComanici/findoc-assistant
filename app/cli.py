"""Command line entry point: python -m app.cli <command>."""

import argparse
import logging

import psycopg

from app.config import get_settings
from app.embeddings import cosine_similarity, get_embedder
from app.embeddings.indexer import Progress, embed_pending
from app.embeddings.ratelimit import RateLimiter
from app.ingestion.download import download_missing
from app.ingestion.pipeline import ingest
from app.ingestion.sources import load_sources
from app.migrations import migrate


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="python -m app.cli")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("migrate", help="apply pending database migrations")
    commands.add_parser("download", help="download source PDFs that are not on disk yet")
    commands.add_parser(
        "embed-check", help="embed a question and three passages and rank them by similarity"
    )
    embed_parser = commands.add_parser(
        "embed", help="compute embeddings for chunks that do not have one yet (resumable)"
    )
    embed_parser.add_argument(
        "--limit", type=int, metavar="N", help="stop after N chunks (useful for a first try)"
    )
    ingest_parser = commands.add_parser("ingest", help="extract, chunk and store source PDFs")
    ingest_parser.add_argument("--only", nargs="+", metavar="ID", help="ingest only these ids")
    ingest_parser.add_argument(
        "--force", action="store_true", help="re-ingest even if the file has not changed"
    )
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    settings = get_settings()

    if args.command == "migrate":
        applied = migrate(settings.database_url, settings.migrations_dir)
        print(f"applied {len(applied)} migration(s): {', '.join(applied) or '-'}")
        return

    if args.command == "embed-check":
        embed_check(settings)
        return

    if args.command == "embed":
        embed(settings, args.limit)
        return

    sources = load_sources(settings.sources_file)
    if args.command == "download":
        report = download_missing(sources, settings.data_dir)
        print(
            f"downloaded: {len(report.downloaded)}, already present: {len(report.already_present)}"
        )
        if report.failed:
            by_id = {s.id: s for s in sources}
            print(f"\nCould not download {len(report.failed)} file(s). Open each link in a browser")
            print(f"and save the PDF in {settings.data_dir} under the name shown:\n")
            for source_id, reason in report.failed.items():
                source = by_id[source_id]
                print(f"  {source.file}  ({reason})")
                print(f"    {source.url or '(no link)'}")
            parser.exit(1)
        return

    if args.only:
        unknown = set(args.only) - {s.id for s in sources}
        if unknown:
            parser.error(f"unknown source id(s): {', '.join(sorted(unknown))}")
        sources = [s for s in sources if s.id in args.only]
    try:
        results = ingest(
            settings.database_url,
            sources,
            settings.data_dir,
            settings.chunk_max_words,
            settings.chunk_overlap_words,
            force=args.force,
        )
    except FileNotFoundError as exc:
        parser.exit(1, f"error: {exc}\n")
    for source_id, result in results.items():
        print(f"{source_id}: {result}")


def _duration(seconds: float | None) -> str:
    if seconds is None:
        return "?"
    minutes = round(seconds / 60)
    return f"{minutes // 60}h {minutes % 60:02d}m" if minutes >= 60 else f"{minutes}m"


def embed(settings, limit: int | None) -> None:
    embedder = get_embedder(settings)
    limiter = RateLimiter(
        settings.embedding_requests_per_minute, settings.embedding_tokens_per_minute
    )

    def report(p: Progress) -> None:
        print(
            f"{p.done}/{p.total} chunks, ~{p.tokens:,} tokens, "
            f"elapsed {_duration(p.elapsed)}, remaining ~{_duration(p.remaining_seconds)}",
            flush=True,
        )

    print(
        f"model {embedder.model}; limits {limiter.requests_per_minute} requests and "
        f"{limiter.tokens_per_minute:,} tokens per minute. Safe to stop with Ctrl+C and rerun."
    )
    with psycopg.connect(settings.database_url, autocommit=True) as conn:
        result = embed_pending(
            conn, embedder, limiter, settings.embedding_batch_size, limit, on_progress=report
        )
    print(f"done: {result.done} chunk(s) embedded")


EMBED_CHECK_QUERY = "Cât profit a obținut banca anul trecut?"
EMBED_CHECK_PASSAGES = [
    "Producția de energie electrică a scăzut din cauza condițiilor hidrologice nefavorabile.",
    "Rezultatul net al grupului bancar s-a ridicat la 3,2 miliarde lei în exercițiul financiar.",
    "Rețeaua de clinici private a deservit mai mulți pacienți decât în anul precedent.",
]


def embed_check(settings) -> None:
    """Show, on three passages, that similarity follows meaning rather than shared words."""
    embedder = get_embedder(settings)
    query = embedder.embed_query(EMBED_CHECK_QUERY)
    passages = embedder.embed_documents(EMBED_CHECK_PASSAGES)
    print(f"model: {embedder.model}, dimensions: {len(query)}")
    print(f"question: {EMBED_CHECK_QUERY}\n")
    ranked = sorted(
        zip(EMBED_CHECK_PASSAGES, passages, strict=True),
        key=lambda pair: cosine_similarity(query, pair[1]),
        reverse=True,
    )
    for passage, vector in ranked:
        print(f"{cosine_similarity(query, vector):.3f}  {passage}")


if __name__ == "__main__":
    main()
