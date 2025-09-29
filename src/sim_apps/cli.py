"""Command line interface for sim-apps."""

from __future__ import annotations

import argparse
import logging
from pathlib import Path
from typing import Sequence

from .filters.group_filters import (
    only_ai_c_groups,
    only_project_groups,
    with_ai_c_but_without_ai_h_mcml,
    with_ai_c_companion,
    with_ai_h_mcml_companion,
)
from .pipelines.email_list import EmailListPipeline
from .sim_integration import SIMClientAdapter


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Command line utilities for SIM API workflows.",
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["ERROR", "WARNING", "INFO", "DEBUG"],
        help="Logging level to use.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    email_parser = subparsers.add_parser("email-list", help="Generate email lists")
    email_parser.add_argument("--service", required=True, help="SIM service name")
    email_parser.add_argument("--project-groups-only", action="store_true")
    email_parser.add_argument("--with-ai-c", action="store_true")
    email_parser.add_argument("--with-ai-h-mcml", action="store_true")
    email_parser.add_argument("--with-ai-c-but-without-ai-h-mcml", action="store_true")
    email_parser.add_argument("--only-ai-c", action="store_true")
    email_parser.add_argument("--minimal-run", action="store_true", help="Process only a small subset for debugging")
    email_parser.add_argument("--unique-emails", action="store_true", help="Ensure the final email list contains unique addresses")
    email_parser.add_argument(
        "--dedup",
        choices=["none", "by-id", "by-primary-email", "by-best-email"],
        default="by-id",
        help="Deduplication strategy",
    )
    email_parser.add_argument("--institution", help="Institution hint", default=None)
    email_parser.add_argument("--domain-hint", help="Preferred domain", default=None)
    email_parser.add_argument("--output", type=Path, help="Write email list to file")
    email_parser.add_argument("--csv", type=Path, help="Write detailed CSV")
    email_parser.add_argument("--stdout", action="store_true", help="Print result to stdout")
    email_parser.add_argument("--dry-run", action="store_true", help="Run without writing files")
    email_parser.add_argument(
        "--debug-intermediate",
        type=Path,
        help="Directory to store intermediate JSON snapshots",
    )
    return parser


def configure_logging(level: str) -> None:
    logging.basicConfig(level=getattr(logging, level.upper()), format="%(levelname)s %(name)s %(message)s")


def _build_group_filters(args: argparse.Namespace) -> Sequence:
    filters = []
    if args.project_groups_only:
        filters.append(only_project_groups())
    if args.with_ai_c:
        filters.append(with_ai_c_companion())
    if args.with_ai_h_mcml:
        filters.append(with_ai_h_mcml_companion())
    if args.with_ai_c_but_without_ai_h_mcml:
        filters.append(with_ai_c_but_without_ai_h_mcml())
    if args.only_ai_c:
        filters.append(only_ai_c_groups())
    return filters


def run_email_list(args: argparse.Namespace) -> int:
    with SIMClientAdapter.from_default() as client:
        pipeline = EmailListPipeline(
            client=client,
            service=args.service,
            group_filters=_build_group_filters(args),
            dedup_strategy=args.dedup,
            institution=args.institution,
            domain_hint=args.domain_hint,
            output_path=args.output,
            csv_path=args.csv,
            emit_stdout=args.stdout,
            minimal_run=args.minimal_run,
            unique_emails=args.unique_emails,
            debug_dir=args.debug_intermediate,
            logger=logging.getLogger("sim_apps.email_list"),
        )
        context = pipeline.run(dry_run=args.dry_run)
    preview = context.get("preview")
    if preview:
        print("Dry run preview:" if args.dry_run else "Result summary:")
        print(f"  Groups before filters: {preview['groups_before']}")
        processed = preview.get("groups_processed")
        if processed is not None:
            print(f"  Groups processed: {processed}")
        print(f"  Groups after filters: {preview['groups_after']}")
        print(f"  Unique members: {preview['unique_members']}")
        sample = preview.get("sample", [])
        if sample:
            print("  Sample emails:")
            for row in sample:
                print(f"    {row.get('person_id')} -> {row.get('chosen_email')} ({row.get('reason')})")
    stdout_output = context.get("stdout_output")
    if stdout_output:
        print(stdout_output)
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    configure_logging(args.log_level)
    if args.command == "email-list":
        return run_email_list(args)
    parser.error("Unknown command")
    return 1


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
