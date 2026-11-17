"""Command line entry point: python -m app.cli <command>."""

import argparse
import logging

from app.config import get_settings
from app.ingestion.download import download_missing
from app.ingestion.pipeline import ingest
from app.ingestion.sources import load_sources
from app.migrations import migrate


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="python -m app.cli")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("migrate", help="apply pending database migrations")
    commands.add_parser("download", help="download source PDFs that are not on disk yet")
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

    sources = load_sources(settings.sources_file)
    if args.command == "download":
        downloaded = download_missing(sources, settings.data_dir)
        print(f"downloaded {len(downloaded)} file(s)")
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


if __name__ == "__main__":
    main()
