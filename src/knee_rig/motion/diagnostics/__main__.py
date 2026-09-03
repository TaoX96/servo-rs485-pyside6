"""Command-line entry point for the one-shot Raspberry Pi diagnostic."""

from __future__ import annotations

import argparse
import json
from collections.abc import Sequence
from pathlib import Path

from knee_rig.motion.diagnostics.read_only import (
    READ_ONLY_REGISTERS,
    DiagnosticConfigError,
    DiagnosticErrorCode,
    load_diagnostic_config,
    plan_read,
    read_once,
    real_serial_factory,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="One-shot symbolic A6-RS FC03 diagnostic; never writes or scans."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    for name in ("validate-config", "read"):
        command = subparsers.add_parser(name)
        command.add_argument("--config", type=Path, required=True)
        command.add_argument(
            "--register",
            choices=tuple(READ_ONLY_REGISTERS),
            required=True,
        )
        if name == "read":
            command.add_argument("--arm-read-only-hardware", action="store_true")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    register = READ_ONLY_REGISTERS[args.register]
    try:
        config = load_diagnostic_config(args.config)
    except DiagnosticConfigError as exc:
        print(
            json.dumps(
                {
                    "ok": False,
                    "error_code": DiagnosticErrorCode.CONFIG_INVALID.value,
                    "message": str(exc),
                    "device_opened": False,
                },
                sort_keys=True,
            )
        )
        return 2
    if args.command == "validate-config":
        print(json.dumps(plan_read(config, register).to_dict(), indent=2, sort_keys=True))
        return 0
    result = read_once(
        config,
        register,
        armed=args.arm_read_only_hardware,
        serial_factory=real_serial_factory,
    )
    print(json.dumps(result.to_dict(), indent=2, sort_keys=True))
    return 0 if result.ok else 2


if __name__ == "__main__":
    raise SystemExit(main())
