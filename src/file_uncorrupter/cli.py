from __future__ import annotations

import argparse
import json
from pathlib import Path

from .db import connect, fetch_summary, latest_run_id, start_run
from .pipeline import RecoveryPipeline
from .reporting import write_attempts_csv, write_json_report


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="file-uncorrupter")
    subparsers = parser.add_subparsers(dest="command", required=True)

    def add_common_scan_args(target: argparse.ArgumentParser) -> None:
        target.add_argument("input_root", type=Path)
        target.add_argument("--recursive", action="store_true")
        target.add_argument("--all-files", action="store_true")
        target.add_argument("--db", type=Path, default=Path("runs.sqlite3"))
        target.add_argument("--engine", default="jpeg-v1")

    scan = subparsers.add_parser("scan")
    add_common_scan_args(scan)

    classify = subparsers.add_parser("classify")
    add_common_scan_args(classify)

    recover = subparsers.add_parser("recover")
    add_common_scan_args(recover)
    recover.add_argument("output_root", type=Path)
    recover.add_argument("--save-raw-candidates", action="store_true")

    report = subparsers.add_parser("report")
    report.add_argument("--db", type=Path, default=Path("runs.sqlite3"))
    report.add_argument("--run-id", type=int)
    report.add_argument("--output-json", type=Path)
    report.add_argument("--output-csv", type=Path)

    return parser


def command_scan(args: argparse.Namespace) -> int:
    pipeline = RecoveryPipeline(engine_name=args.engine)
    records = pipeline.scan_records(args.input_root, recursive=args.recursive, all_files=args.all_files)
    with connect(args.db) as conn:
        run_id = start_run(conn, "scan", args.input_root, None, args.engine)
        classified = pipeline.classify_records(records)
        pipeline.persist_scan(conn, run_id, classified)
        summary = fetch_summary(conn, run_id)
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 0


def command_classify(args: argparse.Namespace) -> int:
    pipeline = RecoveryPipeline(engine_name=args.engine)
    records = pipeline.scan_records(args.input_root, recursive=args.recursive, all_files=args.all_files)
    classified = pipeline.classify_records(records)
    with connect(args.db) as conn:
        run_id = start_run(conn, "classify", args.input_root, None, args.engine)
        pipeline.persist_scan(conn, run_id, classified)
        summary = fetch_summary(conn, run_id)
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 0


def command_recover(args: argparse.Namespace) -> int:
    pipeline = RecoveryPipeline(engine_name=args.engine)
    records = pipeline.scan_records(args.input_root, recursive=args.recursive, all_files=args.all_files)
    classified = pipeline.classify_records(records)
    with connect(args.db) as conn:
        run_id = start_run(conn, "recover", args.input_root, args.output_root, args.engine)
        persisted = pipeline.persist_scan(conn, run_id, classified)
        recovered = 0
        failed = 0
        for file_id, record, data, classification in persisted:
            outcome, raw_candidate_path = pipeline.recover_one(
                record=record,
                data=data,
                classification=classification,
                output_root=args.output_root,
                save_raw_candidates=args.save_raw_candidates,
            )
            pipeline.persist_recovery(conn, run_id, file_id, outcome, raw_candidate_path)
            if outcome.decode.ok:
                recovered += 1
                print(f"OK   {record.relative_path} -> {outcome.decode.output_path} | {outcome.decode.width}x{outcome.decode.height} | {outcome.candidate.strategy_id if outcome.candidate else 'none'} | {outcome.decode.decoder}")
            else:
                failed += 1
                print(f"FAIL {record.relative_path} | {outcome.decode.error}")
        summary = fetch_summary(conn, run_id)
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 0


def command_report(args: argparse.Namespace) -> int:
    with connect(args.db) as conn:
        run_id = args.run_id or latest_run_id(conn)
        if run_id is None:
            raise SystemExit("No runs found.")
        summary = fetch_summary(conn, run_id)
        if args.output_json:
            write_json_report(conn, run_id, args.output_json)
        if args.output_csv:
            write_attempts_csv(conn, run_id, args.output_csv)
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 0


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    if args.command == "scan":
        return command_scan(args)
    if args.command == "classify":
        return command_classify(args)
    if args.command == "recover":
        return command_recover(args)
    if args.command == "report":
        return command_report(args)
    raise SystemExit(f"Unknown command: {args.command}")


if __name__ == "__main__":
    raise SystemExit(main())
