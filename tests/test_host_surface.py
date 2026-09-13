# Copyright (c) 2026 Martial Systems LLC
from __future__ import annotations

from pathlib import Path

REPO = Path(__file__).resolve().parents[1]


def test_demo_does_not_call_teacher_engine() -> None:
    demo = (REPO / "scripts" / "run_demo.py").read_text(encoding="utf-8")
    src = (REPO / "src" / "snn_doom" / "demo").read_text(encoding="utf-8") if False else ""
    demo_pkg = REPO / "src" / "snn_doom" / "demo"
    text = demo
    if demo_pkg.is_dir():
        for p in demo_pkg.rglob("*.py"):
            text += "\n" + p.read_text(encoding="utf-8")
    assert "teacher.tick" not in text
    assert "cast_ray(" not in text
    assert "apply_enemy" not in text
    assert "apply_move" not in text
    assert "paint_frame" not in text


def test_readme_host_contract() -> None:
    text = (REPO / "README.md").read_text(encoding="utf-8")
    assert "inject" in text.lower()
    assert "decode" in text.lower()
    assert "—" not in text
    assert "What it is not" not in text


def test_headless_demo_does_not_inject_fire() -> None:
    demo = (REPO / "scripts" / "run_demo.py").read_text(encoding="utf-8")
    assert "pack_input(0, 0, int(args.fwd), 0)" in demo
    view = (REPO / "src" / "snn_doom" / "demo" / "view.py").read_text(encoding="utf-8")
    assert 'int("space" in pressed or "ctrl" in pressed or "f" in pressed)' in view
    assert 'int("e" in pressed or "q" in pressed)' in view
    assert "pack_input(" in view
    assert "pack_input(0, 0, int(args.fwd), 0)" in demo
