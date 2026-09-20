from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .config import ProjectConfig, healthcheck


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="chemot-align")
    subparsers = parser.add_subparsers(dest="command", required=True)

    for command in ("healthcheck", "print-config"):
        command_parser = subparsers.add_parser(command)
        command_parser.add_argument(
            "--config",
            type=Path,
            default=Path("configs/project.yaml"),
            help="path to the project YAML configuration",
        )

    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        config = ProjectConfig.from_yaml(args.config)
    except (OSError, ValueError) as exc:
        print(
            json.dumps({"status": "error", "error": str(exc)}, ensure_ascii=False),
            file=sys.stderr,
        )
        return 2

    if args.command == "healthcheck":
        payload = healthcheck(config)
    else:
        payload = config.model_dump(mode="json")

    print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
