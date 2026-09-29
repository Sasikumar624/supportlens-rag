import argparse
from dataclasses import asdict
import json
from pathlib import Path

from app.core.logging import configure_logging
from app.db.qdrant import QdrantCollectionConfig
from app.ingestion.indexer import IndexingConfig, build_index_from_sources_csv


REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_SOURCES_CSV = REPO_ROOT / "data" / "sources.csv"


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Build the SupportLens Qdrant index from a sources.csv registry."
    )
    parser.add_argument(
        "--sources-csv",
        type=Path,
        default=DEFAULT_SOURCES_CSV,
        help=f"Path to sources.csv. Defaults to {DEFAULT_SOURCES_CSV}.",
    )
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Delete and recreate the configured Qdrant collection before indexing.",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=64,
        help="Number of Qdrant points to upsert per batch.",
    )
    args = parser.parse_args()

    configure_logging("INFO")
    result = build_index_from_sources_csv(
        args.sources_csv,
        config=IndexingConfig(
            collection=QdrantCollectionConfig.from_settings(),
            reset_collection=args.reset,
            upsert_batch_size=args.batch_size,
        ),
    )
    print(json.dumps(asdict(result), indent=2))


if __name__ == "__main__":
    main()
