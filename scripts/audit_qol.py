#!/usr/bin/env python3
# Copyright (c) 2026 Martial Systems LLC
"""Neuron QoL auditor. Judges a proposal against the frozen stitch. Does not grow the net."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from snn_doom.qol.auditor import (
    audit_proposal,
    load_proposal,
    render_screen,
    scan_dir,
    write_report,
)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="audit-qol")
    p.add_argument("proposal", nargs="?", type=Path, help="proposals/foo.yaml")
    p.add_argument("--scan", type=Path, default=None, help="directory of proposal files")
    p.add_argument("--compare", type=Path, default=None, help="checkpoints/snn_doom_v1.json")
    p.add_argument("--cap", type=int, default=None, help="override named cap (doom.v2_cap is 12000)")
    p.add_argument("--out", type=Path, default=None)
    args = p.parse_args(argv)
    if args.scan is None and args.proposal is None:
        args.scan = ROOT / "proposals"
    reports = []
    if args.scan is not None:
        folder = args.scan
        if not folder.is_dir():
            print(f"missing scan dir {folder}", file=sys.stderr)
            return 2
        reports = scan_dir(folder, compare=args.compare, cap=args.cap)
    else:
        path = args.proposal
        if path is None or not path.is_file():
            print("need a proposal file or --scan DIR", file=sys.stderr)
            return 2
        reports = [audit_proposal(load_proposal(path), compare=args.compare, cap=args.cap)]
    dest = args.out
    index = []
    for report in reports:
        js, md = write_report(report, dest)
        print(render_screen(report))
        print(f"wrote {js} {md}")
        print()
        index.append(
            {
                "name": (report.get("proposal") or {}).get("name"),
                "verdict": report.get("verdict"),
                "score": report.get("score"),
                "headroom": report.get("headroom"),
                "json": str(js),
            }
        )
    if len(reports) > 1:
        out_dir = dest or (ROOT / "logs" / "qol_audit")
        (out_dir / "index.json").write_text(json.dumps(index, indent=2) + "\n", encoding="utf-8")
        lines = ["# QoL audit scan", ""]
        for row in index:
            lines.append(f"- {row['name']}: {row['verdict']} (score {row['score']:.2f}, headroom {row['headroom']})")
        (out_dir / "index.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
        print("scan", json.dumps(index, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
